'''
# Implemented via AWSPE-5777
# Acceptance Criteria:

STEP 1 StateMachineSSMInstall

'''

import re
import boto3, json
sg_client = boto3.client('stepfunctions')
from install_ssm_using_user_data import install_ssm

# Send task success to step function
def send_task_success(taskToken, payload_json):
    try:
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
        parametersetname = event['ParameterSetName']
        error = {}
        error['InstanceId'] = instanceId
        if parametersetname == 'None':
            error['Error'] = 'Lambda exception Occurred'
            error['Cause'] = "ParameterSetName is None.Please delete from DynamoDB all tables before proecssing"
            send_task_failure(taskToken, json.dumps(error), error['Cause'] )
        region = context.invoked_function_arn.split(':')[3]
        install_ssm_obj = install_ssm(region)

        ec2_resource = boto3.resource('ec2')
        ec2_client = boto3.client('ec2')
        instance = ec2_resource.Instance(instanceId)

        statustypes = ["running","shutting-down","terminated","stopping","stopped"]
        instancestatus = instance.state['Name']

        print("The status of the instance {id} is - {status}".format(id=instanceId,status=instancestatus))

        if instancestatus not in statustypes:
            instance.wait_until_running()

            instance = ec2_resource.Instance(instanceId)
            instancestatus = instance.state['Name']
            print("The status of the instance {id} is - {status}".format(id=instanceId,status=instancestatus))

            instancestatuswaiter = ec2_client.get_waiter('instance_status_ok')
            instancestatuswaiter.wait(InstanceIds=[instanceId])
            print("Instance status check is completed")

            systemstatuswaiter = ec2_client.get_waiter('system_status_ok')
            systemstatuswaiter.wait(InstanceIds=[instanceId])
            print("system status check is completed")

        
        print("State Machine Step 1 starting for Instance Id ", instanceId)
        report = install_ssm_obj.exec_install_ssm(instanceId)
        print(report)
        if report:
            if 'StateSuccessFail' in report:
                if(report['StateSuccessFail'] in 'FAIL'):
                    raise Exception(report['StateDetail'])
                #Prepare the payload for success
                StateName = report.get('StateName','InstallSSM')
                payload_json = {'InstanceId':instanceId, 'TaskToken':taskToken, 'ParameterSetName': event['ParameterSetName'],
                                'StateMachine':StateName, 'Message': 'Install SSM Report - Success'}

                #send task success to Task Token
                send_task_success(taskToken, payload_json)
            
            return "Lambda executed successfully"
        else:
            error['Error'] = 'Lambda exception Occurred'
            send_task_failure(taskToken, json.dumps(error))
    except Exception as e:
        print(e)
        error['Error'] = str(e)
        send_task_failure(taskToken, json.dumps(error), str(e))
        raise
        