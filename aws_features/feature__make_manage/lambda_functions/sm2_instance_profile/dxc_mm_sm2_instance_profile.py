'''
- identify any pre-existing instance profile and append (do not overwrite) DXC roles to the pre-existing instance profile, 
ensuring the pre-existing profile permissions are not lost and correct permissions for SSM and Offering are added.
- if no pre-existing instance profile exists, assign a DXC instance profile to the instance

Sample Request event:
        {
          "InstanceId": "<instanceId>",
          "ParameterSetName":"default",
          "TaskToken": "<stepfuntion-tasktoken>"
        }
'''

import json, os
from boto_helper import boto_helper
import boto3
from botocore.config import Config

boto_obj = boto_helper()

def lambda_handler(event, context):

    try:

        print('Received Event:', event)
        taskToken = event['TaskToken']
        instanceId = event['InstanceId']
        param_set_name = event['ParameterSetName']
        
        error = {}
        error['InstanceId'] = instanceId

        offerings_def_inst_role_arn = os.environ['DefaultInstanceProfileArn']
        offerings_def_inst_role = os.environ['DefaultInstanceProfile']
        offerings_default_role = os.environ['DefaultInstanceRole']

        ddb_report_tbl = os.environ['ddbInstRepTableName']
        ddb_param_set_tbl = os.environ['ddbParamSetTableName']
        ddb_inst_info = os.environ['ddbInstInfoTableName']

        config = Config(retries=dict(max_attempts=10,mode='standard'))
        ddb_rsc = boto3.resource('dynamodb', config=config)


        param_set_record = boto_obj.check_db_entry_exists(ddb_param_set_tbl, 'ParameterSetName', param_set_name)

        if(param_set_record is None):
            print('ParameterSetName - {} is not available in DynamoDB table - {}'.format(param_set_name, ddb_param_set_tbl))
            raise "ParameterSetName is not available in DynamoDB table"

        offerings_def_role = boto_obj.get_role_instance_profile(offerings_def_inst_role)

        offerings_def_inst_role_policies = boto_obj.list_attached_policies(offerings_def_role)
        print('offerings_def_inst_role_policies:',offerings_def_inst_role_policies)

        offerings_def_inst_role_inline_policies = boto_obj.list_attached_inline_policies(offerings_def_role)
        print('offerings_def_inst_role_inline_policies:',offerings_def_inst_role_inline_policies)

        inst_attached_role_arn = boto_obj.describe_iam_instance_profile_associations(instanceId)

        inst_attached_role = None

        if(inst_attached_role_arn):
            var_to_get_inst_attached_role = inst_attached_role_arn.split(':')[-1].replace('instance-profile/','')
            inst_attached_role = boto_obj.get_role_instance_profile(var_to_get_inst_attached_role)

        print('inst_attached_role:',inst_attached_role)

        ddb_inst_info_table_obj = ddb_rsc.Table(ddb_inst_info)
        response = ddb_inst_info_table_obj.get_item(Key={
                    'InstanceId': instanceId
                })
        instance_data = response['Item']
        print(instance_data)

        osname = instance_data['os-name'].strip()            
        osarch = instance_data['os-arch'].strip()
        print('osname is: {} and osarch is: {}'.format(osname,osarch))

        if(inst_attached_role == None):

            boto_obj.associate_iam_instance_profile(offerings_def_inst_role_arn, 
                                           offerings_def_inst_role,
                                           instanceId)

            if('windows' in osname.lower()):
                boto_obj.ssm_send_cmd(instanceId, 'Windows')
            else:
                boto_obj.ssm_send_cmd(instanceId)
            print('AWSMS Offerings Default Instance role attached SUCCESSFULLY')

        elif inst_attached_role and offerings_def_inst_role_arn == inst_attached_role_arn:
            print('AWSMS Offerings Default Instance role already attached to instance')

        elif inst_attached_role and offerings_def_inst_role_arn != inst_attached_role_arn:
            print('Instance has role but its different. Attached the required policies')
            
            print('attaching managed polices')
            inst_attached_role_policies = boto_obj.list_attached_policies(inst_attached_role)
            inst_attached_role_pol_names = [obj['PolicyName'] for obj in inst_attached_role_policies]

            for policy in offerings_def_inst_role_policies:
                if policy['PolicyName'] not in inst_attached_role_pol_names:
                    boto_obj.attach_policy_to_role(inst_attached_role, policy['PolicyArn'])
            print('attaching managed polices COMPLETED')
            
            print('attaching inline policies')
            inst_attached_role_inline_policies = boto_obj.list_attached_inline_policies(inst_attached_role)

            for inline_policy in offerings_def_inst_role_inline_policies:
                if inline_policy not in inst_attached_role_inline_policies:
                    boto_obj.attach_inline_policy_to_role(offerings_default_role,inst_attached_role,inline_policy)

            print('attaching inline policies COMPLETED')

            if('windows' in osname.lower()):
                boto_obj.ssm_send_cmd(instanceId, 'Windows')
            else:
                boto_obj.ssm_send_cmd(instanceId)
            print('Default Instance Role policies are attached to the Instance role - {}'.format(inst_attached_role))

        else:
            print('Unknown exception while attaching Default Instance Role')
            raise 

        boto_obj.update_report_table(ddb_report_tbl, instanceId, 'SUCCESS', 'DefaultInstanceRole attached successfully')
        payload_json = {'InstanceId':instanceId, 'TaskToken':taskToken, 'ParameterSetName': event['ParameterSetName'],
                            'StateMachine':'InstanceProfile', 'Message':'InstanceProfile Attaching - Success'}
        boto_obj.send_task_success(taskToken, payload_json)

        print('process completed')
        #return "Lambda executed Successfully"

    except Exception as e:
        
        error['Error'] = 'Instance Profile attched exception Occurred '
        boto_obj.update_tag(instanceId, 'dxc_make_manage','Fail')
        boto_obj.update_report_table(ddb_report_tbl, instanceId, 'FAIL', str(e))
        boto_obj.send_task_failure(taskToken, json.dumps(error), str(e))
        print('Error lambda_handler() ', e)