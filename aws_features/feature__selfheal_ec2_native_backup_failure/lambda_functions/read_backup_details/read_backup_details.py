"""
This lambda function fetches the OS details of the EC2 instance.
Reads the current value of the EC2 instance tags LinuxNativeBackupLevel / WindowsNativeBackupLevel
Fetches the values of Backup Vault name, backup IAM role name, retention period from the
AccountFeatureDefinition DynamoDB table

This Lambda is a part of Selfheal EC2 NativeBackupFailure

In Diagnosis state machine (dxcms_sh_nbf_sfn_diagnosis):
gets executed after - Start
On successful check, next state - CheckTags is called.
On FAILURE, next State - TriggerNotificationSfnWError and NotifyForLambaFunctionFailure.
"""

import json
import boto3
import traceback
import os
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))

ec2_client = boto3.client('ec2', config=config)
ec2_resource = boto3.resource('ec2', config=config)
dynamodb_client =  boto3.client('dynamodb', config=config)
region = os.environ['AWS_REGION']

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
        input = str(e)[:200]
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

def get_backup_level(instance_id, instance_os_type):
    try:
        print("get_backup_level() triggered.")
        flag = False
        instance = ec2_resource.Instance(instance_id)
        if (instance_os_type == 'windows'):
            tag_name = 'WindowsNativeBackupLevel'
        else:
            tag_name = 'LinuxNativeBackupLevel'
        tags = instance.tags
        if tags:
            for tag in tags:
                if(tag['Key']==tag_name):
                    flag = True
                    break
        if flag:
            print("Backup Level is - " + str(tag['Value']))
            return(tag['Value'])
        else:
            print("Tag not found.")
            raise Exception(f"'{tag_name}' tag not found on instance.")
    
    except Exception as e:
        print("Error get_backup_level() - ",e)
        print("Error caught. Taking default value 2.")
        return '2'

def read_backup_details_dynamodb(instance_os_type, backup_level):
    print("read_backup_delete_after_days() triggered.")
    if instance_os_type == "linux" and backup_level == "1":
        table_key = "NativebackupEc2LinuxLevel1"
        vault_name = "Ec2LinuxLevel1BackUpVault"
        backup_role_name = f"EC2LinuxLevel1NativeBackup-{region}"
    elif instance_os_type == "linux" and backup_level == "2":
        table_key = "NativebackupEc2LinuxLevel2"
        vault_name = "Ec2LinuxLevel2BackUpVault"
        backup_role_name = f"EC2LinuxLevel2NativeBackup-{region}"
    elif instance_os_type == "windows" and backup_level == "1":
        table_key = "NativebackupEc2WindowsLevel1"
        vault_name = "Ec2WindowsLevel1BackUpVault"
        backup_role_name = f"EC2WindowsLevel1NativeBackup-{region}"
    else:
        table_key = "NativebackupEc2WindowsLevel2"
        vault_name = "Ec2WindowsLevel2BackUpVault"
        backup_role_name = f"EC2WindowsLevel2NativeBackup-{region}"
    print(f"table key is {table_key}")
    try:
        feature_definition_reponse = dynamodb_client.get_item(
            TableName='AccountFeatureDefinitions',
            Key={'Feature': {'S': table_key}}
        )
        days = int(feature_definition_reponse['Item']['FeatureParams']['M']['pfBackupDeleteAfterDays']['M']['Default']['N'])
        print(f"delete after days for backups is {days}")
        vault_name = feature_definition_reponse['Item']['FeatureParams']['M']['pfBackupVaultName']['M']['Default']['S']
        print(f"backup vault name is {vault_name}")
        retention_period = {"DeleteAfterDays": days}
        return retention_period, vault_name, backup_role_name
    except Exception as e:
        print("Error read_backup_delete_after_days() - ",e)
        print("Error while reading retention period from dynamodb, taking default value as 30")
        retention_period = {"DeleteAfterDays": 30}
        return retention_period, vault_name, backup_role_name

def lambda_handler(event, context):
    global task_token,instance_id
        
    print("input recieved to this script - " + str(event))
    task_token = event["token"]
    event = event["Payload"]
    instance_id = event['instance_id']
    try:
        instance = ec2_resource.Instance(instance_id)
        instance_state = instance.state['Name']
        instance_os_type = 'linux'
        if instance.platform:
            if (instance.platform.lower().find('win') != -1):
                instance_os_type = 'windows'
        print(f"Instance Platform Type is {instance_os_type}")
        
        backup_level = get_backup_level(instance_id, instance_os_type)
        retention_period, vault_name, backup_role_name = read_backup_details_dynamodb(instance_os_type, backup_level)

        event["backup_level_assigned"] = backup_level
        event["instance_os_type"] = instance_os_type
        event["retention_period"] = retention_period
        event['vault_name'] = vault_name
        event['backup_role_name'] = backup_role_name
        event['instance_state'] = instance_state
        return success_token(event,task_token)
    
    except Exception as e:
        print("Error lambda_handler() - ",e)
        error_status = traceback.format_exc()
        input = str(e)[:200]
        return failure_token(task_token, input, error_status)