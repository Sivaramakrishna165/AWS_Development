'''
This Lambda function is used to trigger ssm run command with a document which list down
all the volumes mounted in the instance.

This Lambda is a part of Selfheal EC2 NativeBackupFailure

In Diagnosis state machine (dxcms_sh_nbf_sfn_diagnosis):
gets executed after - CheckCLI State
On successful check, next state - WaitforSSMCmd and the CheckUnmountedVolumes is called.
On FAILURE, next State - TriggerNotificationSfnWError and NotifyForLambaFunctionFailure.
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
        failure_token(task_token, str(e)[:200], traceback.format_exc())

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
        return failure_token(task_token, str(e)[:200], error_status)