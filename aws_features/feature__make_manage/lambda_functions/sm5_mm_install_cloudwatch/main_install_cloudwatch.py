'''
# Implemented via AWSPE-5779, AWSPE-6010  and AWSPE-6044
# Acceptance Criteria:

STEP 5 StateMachineInstallCloudwatch

Configure the instance as done in the Simple Workload Template User Data section (same as AWSPE-5672)
ApplyMonitoring - have Cloudwatch agent installed.

# Statemachine Lambda splitup implemented via [AWSPE-6392]
'''
import boto3, json
import os
from botocore.config import Config
from apply_instance_monitoring import instance_monitoring

sg_client = boto3.client('stepfunctions')

config = Config(retries=dict(max_attempts=10,mode='standard'))
ec2 = boto3.resource('ec2')
ddb = boto3.resource('dynamodb', config=config)
ddb_inst_info = os.environ['ddbInstInfoTableName']
ddb_param_set = os.environ['ddbParamSetTableName']
customer_bucket = os.environ['evDXCS3CustomerBucketName']

# Send task success to step function
def send_task_success(taskToken, payload_json):
    try:
        print("send_task_success Execution started")
        response = sg_client.send_task_success(
            taskToken=taskToken,
            output = json.dumps(payload_json)
        )
        print('Task SUCCESS token sent - ',response)

    except Exception as e:
        print('Error send_task_success()-',e)

# Send task failure to step function
def send_task_failure(taskToken, error, cause):
    try:
        print("send_task_failure Execution started")
        response = sg_client.send_task_failure(
            taskToken=taskToken,
            error = error,
            cause = cause
        )
        print('Task FAILURE token sent - ',response)

    except Exception as e:
        print('Error send_task_success()-',e)


def lambda_handler(event, context):
    try:
        print('Event - ', event)
        taskToken = event['TaskToken']
        instanceId = event['InstanceId']
        StateName = "InstallCloudwatch"
        
        error = {}
        error['InstanceId'] = instanceId

        StateDetail = ''
        StateSuccessFail = ''
        ApplyMonitoring = 0  

        
        ddb_inst_info_table_obj = ddb.Table(ddb_inst_info)
        response = ddb_inst_info_table_obj.get_item(Key={
                    'InstanceId': instanceId
                    })
        instance_data = response['Item']

        if instance_data:
            ParameterSetName = instance_data['ParameterSetName']
            os_name = instance_data['os-name'].strip()
            osname = os_name.upper()
            osarch = instance_data['os-arch'].strip()

            ddb_param_set_table_obj = ddb.Table(ddb_param_set)
            param_response = ddb_param_set_table_obj.get_item(Key={
                            'ParameterSetName': ParameterSetName
                            })
            param_response_data = param_response['Item']
            param_response_data['OSName'] = osname            

            for k,v in param_response_data.items():
                if k =='ApplyMonitoring' and v:
                    ApplyMonitoring = 1

            StateSuccessFail = 'SUCCESS'

        if ApplyMonitoring:
            region = context.invoked_function_arn.split(':')[3]
            print(instanceId)
            print("############################### Monitoring START #######################")            
            instance_monitoring_obj = instance_monitoring(config,region)
            if(osname == 'WINDOWS'):
                StateDetail,State_Success_Fail = instance_monitoring_obj.exec_instance_monitoring(instanceId,osname,osarch, '_cmd1')
                StateSuccessFail=State_Success_Fail.upper()
                print("CMD Status ", StateDetail,StateSuccessFail)
                StateDetail,State_Success_Fail = instance_monitoring_obj.exec_instance_monitoring(instanceId,osname,osarch, '_cmd2')
                StateSuccessFail=State_Success_Fail.upper()
            else:
                StateDetail,State_Success_Fail = instance_monitoring_obj.exec_instance_monitoring(instanceId,osname,osarch)
                StateSuccessFail=State_Success_Fail.upper()
                print("MONITORING Status ", StateDetail,StateSuccessFail)
                print("################################ MONITORING END #######################")

        if StateSuccessFail:
            if 'FAIL' in StateSuccessFail:                
                raise Exception(StateDetail)
            #Prepare the payload for success
            StateName = StateName
            payload_json = {'InstanceId':instanceId, 'TaskToken':taskToken, 'ParameterSetName': event['ParameterSetName'],
                            'StateMachine': StateName , 'Message': 'Installing Cloudwtch done successfully'}

            #send task success to Task Token
            print("Sending data for Send TASK STATUS")
            send_task_success(taskToken, payload_json)
            print("Lambda executed successfully")
            return "Lambda executed successfully"
        else:
            error['Error'] = 'Instance Tagging Lambda exception Occurred'
            print("error",error)
            send_task_failure(taskToken, json.dumps(error))

    except Exception as e:
        print(e)
        error['Error'] = 'Installing Cloudwtch Lambda exception Occurred'
        send_task_failure(taskToken, json.dumps(error), str(e))
        raise