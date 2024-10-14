'''
# Implemented via AWSPE-5779, AWSPE-6010  and AWSPE-6044
# Acceptance Criteria:

STEP 3 StateMachineInstallFalcon

Configure the instance as done in the Simple Workload Template User Data section (same as AWSPE-5672)

ApplyendpointProtection (install falcon agent)if no pre-existing instance profile exists, assign a DXC instance profile to the instance
apply hardening if possible. 
'''
import boto3, json
from boto_helper import boto_helper

sg_client = boto3.client('stepfunctions')

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
        StateName = "InstallFalcon"
        
        error = {}
        error['InstanceId'] = instanceId
        
        region = context.invoked_function_arn.split(':')[3]
        boto_obj = boto_helper(region)
        print(instanceId)
        print("############################### Check instance running then TAGGING START #######################")
        report = boto_obj.install_falcon(instanceId,StateName)
        print("############################### Check instance running then TAGGING END #######################")
        print("################################ REPORT START #######################")
        print(report)
        print("################################ REPORT END #######################")
        if report:
            if 'StateSuccessFail' in report:
                if(report['StateSuccessFail'] in 'FAIL'):
                    raise Exception(report['StateDetail'])
            #Prepare the payload for success
            StateName = report.get('StateName','InstallFalcon')
            payload_json = {'InstanceId':instanceId, 'TaskToken':taskToken, 'ParameterSetName': event['ParameterSetName'],
                            'StateMachine': StateName , 'Message': 'Installing Falcon done successfully'}

            #send task success to Task Token
            print("Sending data for Send TASK STATUS")
            send_task_success(taskToken, payload_json)
            print("Lambda executed successfully")
            return "Lambda executed successfully"
        else:
            error['Error'] = 'Installing Falcon Lambda exception Occurred'
            print("error",error)
            send_task_failure(taskToken, json.dumps(error))

    except Exception as e:
        print(e)
        error['Error'] = 'Instance Tagging Lambda exception Occurred'
        send_task_failure(taskToken, json.dumps(error), str(e))
        raise
        