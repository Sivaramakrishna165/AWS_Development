'''
Boto Helper class contain all the supported aws api operations
'''

import boto3, json, time
from botocore.config import Config
from boto3.dynamodb.conditions import Attr
from datetime import datetime

class boto_helper():
    
    def __init__(self,region='us-east-1'):
        config = Config(retries=dict(max_attempts=10,mode='standard'))
        self.ec2_client = boto3.client('ec2', config=config)
        self.ssm_client = boto3.client('ssm', config=config)
        self.st_client = boto3.client('stepfunctions',config=config)
        self.ddb = boto3.resource('dynamodb', config=config)
        self.iam_client = boto3.client('iam',region_name=region, config=config)
        self.iam_resource = boto3.resource('iam',region_name=region, config=config)
    
    def check_db_entry_exists(self, tbl_name, item_name, item_value):
        result = False
        try:
            table = self.ddb.Table(tbl_name)
            get_item_response = table.get_item(Key={item_name: item_value})
            if('Item' not in get_item_response):
                raise Exception('{} not vailable in ddbtable - {}'.format(item_value, tbl_name))
            if get_item_response['Item'][item_name] == item_value:
                return get_item_response['Item']
            else:
                print('Item %s not found' % item_name)
                return None
        except Exception as e:
            print("Error check_db_entry_exists() - {}".format(e))
            return False
            
    def get_role_instance_profile(self, profile_name):
        try:
            response = self.iam_client.get_instance_profile(
                InstanceProfileName=profile_name
            )
            return response['InstanceProfile']['Roles'][0]['RoleName']
        except Exception as e:
            print('Error get_role_instance_profile() -',e)
            raise

    def list_attached_policies(self, role_name):
        try:
            response = self.iam_client.list_attached_role_policies(RoleName=role_name)
            return response['AttachedPolicies']
        except Exception as e:
            print('Error list_attached_policies() -',e)
            raise
    
    def list_attached_inline_policies(self, role_name):
        try:
            response = self.iam_client.list_role_policies(RoleName=role_name)
            return response['PolicyNames']
        except Exception as e:
            print('Error list_attached_inline_policies() -',e)
            raise

    def attach_policy_to_role(self, role_name, policy_arn):
        try:
            self.iam_client.attach_role_policy(
                                    RoleName=role_name,
                                    PolicyArn=policy_arn
                                )
        except Exception as e:
            print('Error attach_policy_to_role() -',e)
            raise
    
    def attach_inline_policy_to_role(self, offerings_default_role, inst_attached_role, inline_policy):
        try:
            response = self.iam_client.get_role_policy(
                                RoleName=offerings_default_role,
                                PolicyName=inline_policy
                            )
            print('policy doc is:', response['PolicyDocument'])
            self.iam_client.put_role_policy(
                                RoleName=inst_attached_role,
                                PolicyName=inline_policy,
                                PolicyDocument=json.dumps(response['PolicyDocument']) 
                            )

        except Exception as e:
            print('Error attach_inline_policy_to_role() -',e)
            raise

    def describe_iam_instance_profile_associations(self, instance_id):
        try:
            response = self.ec2_client.describe_iam_instance_profile_associations(            
                Filters=[
                    {
                        'Name': 'instance-id',
                        'Values': [instance_id]
                    },
                ]
            )
            if(response['IamInstanceProfileAssociations']):
                return response['IamInstanceProfileAssociations'][0]['IamInstanceProfile']['Arn']
            else:
                return None
        except Exception as e:
            print('Error describe_iam_instance_profile_associations() -',e)
            raise

    def associate_iam_instance_profile(self, profile_arn, profile_name, instance_id):
        try:
            self.ec2_client.associate_iam_instance_profile(
                IamInstanceProfile={
                    'Arn': profile_arn,
                    'Name': profile_name
                },
                InstanceId=instance_id
            )
            return True
        except Exception as e:
            print('Error associate_iam_instance_profile() -',e)
            raise

    def ssm_send_cmd(self, instance_id, plt_name=None):
        try:
            status = ''

            waiter = self.ssm_client.get_waiter('command_executed')

            if(plt_name == 'Windows'):
                DocumentName = 'AWS-RunPowerShellScript'
                cmd = 'get-wmiobject -class win32_logicaldisk'
            else:
                DocumentName='AWS-RunShellScript'
                cmd = 'df -h'
            
            send_cmd_attempt = 0
            while True:
                send_cmd_attempt += 1

                try:

                    response = self.ssm_client.send_command(InstanceIds=[instance_id],
                                        DocumentName=DocumentName,
                                        TimeoutSeconds = 30,
                                        Parameters={'commands': [cmd]})
                    command_id = response['Command']['CommandId']
                    print('response:',response)
                    print('command_id:',command_id)
                    
                    #self.ssm_client.command_executed()
                    waiter.wait(
                        CommandId=command_id,
                        InstanceId=instance_id,
                        #PluginName='string',
                        WaiterConfig={
                            'Delay': 10,
                            'MaxAttempts': 10
                        }
                    )
                    
                    output = self.ssm_client.get_command_invocation(
                        CommandId=command_id,
                        InstanceId=instance_id)
                        
                    print('output:',output)
                    status = output['Status']
                    if(status == 'Success'):
                        return True

                except Exception as e:
                    print('Error ssm_send_cmd() -',e)
                    pass 
                if(send_cmd_attempt>20):
                    raise Exception('Default Instance Role/Policies attached but Send command execution failed. Please check the SSM agent status')
                else:
                    time.sleep(30)
            
        except Exception as e:
            print('Error ssm_send_cmd() ',str(e))
            raise

    # Update the Tag
    def update_tag(self, resource, key, value):
        try:
            update_tag_response = self.ec2_client.create_tags(
                Resources=[
                    resource,
                ],
                Tags=[
                    {
                        'Key': key,
                        'Value': value
                    },
                ]
            )
            print('Tag - "{}:{}" updated on resource - {}'.format(key, value, resource))
        except Exception as e:
            print("Error in update_tag", e)

    # Update records to table
    def update_report_table(self, tbl_name, instance_id, status, state_detail):
        try:
            table = self.ddb.Table(tbl_name)
            currentDT = datetime.now()
            date_time = currentDT.strftime('%m-%d-%Y_%H%M%S')
            
            table.update_item(
                Key={
                    'InstanceId': instance_id
                },
                UpdateExpression='SET ModifyTime=:time, StateName=:state, StateSuccessFail=:status, StateDetail=:detail',
                ExpressionAttributeValues={
                    ':time': date_time,
                    ':state': 'InstanceProfile',
                    ':status': status,
                    ':detail': state_detail
                }
            )
            print('DDB Table - {} updated successfully for insatnceId - {}'.format(tbl_name, instance_id))
        except boto3.exceptions.botocore.client.ClientError as e:
            print("Error updating item: %s" % e)
            raise UpdateItemException("Error: %s" % e)


    # Send task success to step function
    def send_task_success(self, taskToken, payload_json):
        try:
            response = self.st_client.send_task_success(
                taskToken=taskToken,
                output = json.dumps(payload_json)
            )
            print('Task SUCCESS token sent - ',response)
    
        except Exception as e:
            print('Error send_task_success()-',e)
            raise

    # Send task failure to step function
    def send_task_failure(self, taskToken, error, cause):
        try:
            response = self.st_client.send_task_failure(
                taskToken=taskToken,
                error = error,
                cause = cause
            )
            print('Task FAILURE token sent - ',response)
    
        except Exception as e:
            print('Error send_task_success()-',e)
