"""
This Lambda function is used to check the Tag 'EbsVolumeBackupLevel' for an ec2 instance
and if this tag is present, returns the value (which can be '1' or '2')
if the value is 1 triggers level1 backup.
if the value is 2 triggers level2 backup.

This Lambda is a part of Selfheal ec2 backup failure.
In dxcms_sh_bf_sfn_execute_backup state machine (ChooseBackupLevel)
gets executed after ListExcessiveSnapshotids

Input event of the lambda function is:
    {
        "instance_id": "<instance_id>",
    }

In dxcms_sh_bf_sfn_execute_backup 
On successful check,next state - TriggerBackup is called
On FAILURE, next State ChooseBackupLevelError and then NotifyForLambaFunctionFailure.

"""

import json
import boto3
import traceback
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))

ec2_client = boto3.client('ec2', config=config)
ec2_resource = boto3.resource('ec2', config=config)

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

def get_backup_level(instance_id):
    try:
        print("get_backup_level() triggered.")
        flag = False
        instance = ec2_resource.Instance(instance_id)
        tags = instance.tags
        if tags:
            for tag in tags:
                if(tag['Key']=='EbsVolumeBackupLevel'):
                    flag = True
                    break
        if flag:
            print("Backup Level is - " + str(tag['Value']))
            return(tag['Value'])
        else:
            print("Tag not found.")
            raise Exception(f"'EbsVolumeBackupLevel' tag not found on instance {instance_id}. Taking default value as 2.")
    
    except Exception as e:
        print("Error get_backup_level() - ",e)
        print("Error caught. Taking default value 2.")
        return '2'

def lambda_handler(event, context):
    global task_token,instance_id
        
    print("input recieved to this script - " + str(event))
    task_token = event["token"]
    event = event["Payload"]
    instance_id = event['instance_id']
    try:
        Backup_level = get_backup_level(instance_id)

        event["backup_level_assigned"] = Backup_level
        return success_token(event,task_token)
    
    except Exception as e:
        print("Error lambda_handler() - ",e)
        error_status = traceback.format_exc()
        input = {"error" : f"Error lambda_handler() - {str(e)}", "resource_id" : instance_id, "resource_type" : "EC2 Instance"}
        return failure_token(task_token, input, error_status)