'''
This Lambda function is used to trigger ssm run command with a document which list down
all the volumes mounted in the instance.

In dxcms_sh_bf_sfn_diagnosis state machine(Triggerunmountedvolcheck)
gets executed after CheckCLI  state.

Input event of the lambda function is:
    {
        "instance_id":"<instance-id>", 
    }

In Diagnosis state machine,
On successful check, next state - waitforSSMcommand to checkunmountedvolumes is called.
On FAILURE, next State TriggerunmountedvolcheckError and then NotifyForLambaFunctionFailure.

'''

import json
import os
import boto3
import traceback
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))

ssm_client = boto3.client('ssm', config=config)
ec2_resource = boto3.resource('ec2', config=config)

log_group_name = os.environ['log_group_name']
windows_document_name = os.environ['windows_document_name']
# log_group_name = "check_unmounted_volumes_log_group"
# windows_document_name = "CheckWindowsMountedVolumes"

def success_token(event,task_token):
    try:
        print("success_token() triggered.")
        sf = boto3.client('stepfunctions',config=config)
        sf_output = json.dumps(event)
        sf_response = sf.send_task_success(
            taskToken=task_token,
            output=str(sf_output)
        )
        print("success task token sent - ", sf_response)
        return sf_response
    except Exception as e:
        print("Error success_token() - ",e)
        print("not able to send task success token.")
        input = {"error" : str(e), "resource_id" : instance_id, "resource_type" : "EC2 Instance"}
        failure_token(task_token, input, traceback.format_exc())

def failure_token(taskToken, error, err_cause):
    try:
        print("failure_token() triggered.")
        if isinstance(err_cause, dict):
            cause = json.dumps(err_cause)
        else:
            cause = str(err_cause)
        sf = boto3.client('stepfunctions',config=config)
        sf_response = sf.send_task_failure(
            taskToken=taskToken,
            error = json.dumps(error),
            cause = cause
        )
        print('failure task token sent - ',sf_response)
    except Exception as e:
        print("Error failure_token() - ", e)
        print("not able to send failure task token")
        raise

def trigger_windows_run_command(instance_id):
    try:
        print("trigger_windows_run_command() triggered.")
        
        response=ssm_client.send_command(
            InstanceIds=[instance_id],
            DocumentName=windows_document_name,
            CloudWatchOutputConfig={
                'CloudWatchLogGroupName': log_group_name,
                'CloudWatchOutputEnabled': True
            },
        )

        command_id = command_id = response['Command']['CommandId']

        print(f"command_id: {command_id}")
        return command_id

    except Exception as e:
        print("Error trigger_windows_run_command() - ",e)
        print(f'error executing run command with document "{windows_document_name}"')
        return "Not_Known"

def trigger_linux_run_command(instance_id):
    try:
        print("trigger_linux_run_command() triggered.")
        
        response=ssm_client.send_command(
            InstanceIds=[instance_id],
            DocumentName="AWS-RunShellScript",
            Parameters={'commands': ["lsblk -o NAME,MOUNTPOINT -pJ"]},
            CloudWatchOutputConfig={
                'CloudWatchLogGroupName': log_group_name,
                'CloudWatchOutputEnabled': True
            },
        )

        command_id = command_id = response['Command']['CommandId']

        print(f"command_id: {command_id}")
        return command_id

    except Exception as e:
        print("Error trigger_linux_run_command() - ",e)
        print(f'error executing run command with document "AWS-RunShellScript"')
        return "Not_Known"

def lambda_handler(event, context):
    global task_token,instance_id 
        
    print("input recieved to this script - " + str(event))
    task_token = event["token"]
    event = event["Payload"]
    instance_id = event["instance_id"]
    try:
        instance = ec2_resource.Instance(instance_id)

        if instance.platform:
            if(instance.platform.find('win') != -1):
                print("Windows platform.")
                command_id = trigger_windows_run_command(instance_id)
            else:
                print("Linux platform.")
                command_id = trigger_linux_run_command(instance_id)
        else:
            print("Linux platform.")
            command_id = trigger_linux_run_command(instance_id)
        
        print(command_id)
        event["mounted_vol_command_id"] = command_id
        return success_token(event,task_token)
    
    except Exception as e:
        print("Error lambda_handler() - ",e)
        error_status = traceback.format_exc()
        input = {"error" : f"Error lambda_handler() - {str(e)}", "resource_id" : instance_id, "resource_type" : "EC2 Instance"}
        return failure_token(task_token, input, error_status)


event_win = {"instance_id" : "i-03f2a963369545021"}
event_linux = {"instance_id" : "i-0938fa5628083f05d"}

if __name__ == "__main__":
    lambda_handler(event_win,"i-03f2a963369545021")