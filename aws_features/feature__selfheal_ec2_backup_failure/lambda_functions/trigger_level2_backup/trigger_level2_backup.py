"""
This Lambda function is used to triggers the SSM Run Command with 
documents for taking level 2 backup and other required parameters.

In dxcms_sh_bf_sfn_execute_backup state machine(TriggerLevel2Backup)
gets executed after TriggerBackup state.

Input event of the lambda function is:
    {
        "instance_id":"<instance-id>", 
    }

In executebackup state machine,
On successful check, next state - waitforSSMcommad is called.
On FAILURE, next State TriggerLevel2BackupError and then NotifyForLambaFunctionFailure.

"""

import json
import boto3
import os
import traceback
from datetime import date
from datetime import timedelta
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))

ec2_client = boto3.client('ec2', config=config)
ssm_client = boto3.client('ssm', config=config)
ec2_resource = boto3.resource('ec2', config=config)

log_group_name = os.environ['log_group_name']

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

def getDeleteOnDate(instance_id):
    print("getDeleteOnDate() called")
    error_status = False
    try:
        instance = ec2_resource.Instance(instance_id)
        instanceTags = instance.tags

        today = date.today()
        deleteOnDate = today + timedelta(days=30)

        for i in range(0,len(instanceTags)):
            if (instanceTags[i]['Key'].startswith('RetentionPeriod')):
                deleteOnDate = today + timedelta(days=int(instanceTags[i]['Value']))

        return deleteOnDate, error_status
    
    except Exception as e:
        print("Error getDeleteOnDate() - ",e)
        error_status = traceback.format_exc()
        return '', error_status

def getTags(instance_id):

    print("getTags() called")
    error_status = False
    snapshotTags = []
    try:
        instance = ec2_resource.Instance(instance_id)
        instanceTags = instance.tags
        keepTags = ['Application','Compliance','Environment','InstanceName','Project','Owner']

        for i in range(0,len(instanceTags)):
            for j in range(0,len(keepTags)):
                if (instanceTags[i]['Key'].startswith(keepTags[j])):
                    snapshotTags.append(instanceTags[i])

        deleteOnDate, error_status = getDeleteOnDate(instance_id)
        if not error_status:
            deleteOnTag = {'Key': 'DeleteOn', 'Value': str(deleteOnDate)}
            snapshotTags.append(deleteOnTag)
        else:
            raise Exception("Error getDeleteOnDate() - Error generating DeleteOn tag value.")

        name = 'InstanceId: ' + instance_id
        nameTag = {'Key': 'Name', 'Value': name}
        snapshotTags.append(nameTag)

        levelTag = {'Key': 'snapshotLevel', 'Value': 'level2'}
        snapshotTags.append(levelTag)

        return snapshotTags, error_status
    
    except Exception as e:
        print("Error getTags() - ",e)
        if not error_status:
            error_status = traceback.format_exc()
        return snapshotTags, error_status

def getTagsLinuxString(instance_id):
    print("getTagsLinuxString() called")
    error_status = False
    try:
        snapshotTags, error_status = getTags(instance_id)
        if not error_status:
            snapshotTagsString = 'ResourceType=snapshot,Tags=['

            for i in range(0,len(snapshotTags)):
                key = snapshotTags[i]['Key']
                value = snapshotTags[i]['Value']
                if not value:
                    value = "None"

                snapshotTagsString = snapshotTagsString + '{Key=' + key + ',Value=' + value + '},'
            
            snapshotTagsString = snapshotTagsString[0:len(snapshotTagsString)-1] + ']'

            print("Tags: " + snapshotTagsString)
        else:
            raise Exception(f"Error getTags() - Error while generating tags for instance {instance_id}")
        
        return snapshotTagsString, error_status
    except Exception as e:
        print("Error getTagsLinuxString() - ",e)
        if not error_status:
            error_status = traceback.format_exc()
        return '', error_status

def getTagsWindowsString(instance_id):
    print("getTagsWindowsString() called")
    error_status = False
    try:
        snapshotTags, error_status = getTags(instance_id)
        if not error_status:
            snapshotTagsString = ''

            for i in range(0,len(snapshotTags)):
                key = snapshotTags[i]['Key']
                value = snapshotTags[i]['Value']

                snapshotTagsString = snapshotTagsString + 'Key=' + key + ',Value=' + value + ';'

            snapshotTagsString = snapshotTagsString[0:len(snapshotTagsString)-1]

            print("Tags: " + snapshotTagsString)
        else:
            raise Exception(f"Error getTags() - Error while generating tags for instance {instance_id}")
        
        return snapshotTagsString, error_status
    
    except Exception as e:
        print("Error getTagsWindowsString() - ",e)
        if not error_status:
            error_status = traceback.format_exc()
        return '', error_status


def getOSName(instance_id):
    print("getOSName() called")
    try:
        instance = ec2_resource.Instance(instance_id)
        instanceTags = instance.tags
        OSName = ''

        for i in range(0,len(instanceTags)):
            if (instanceTags[i]['Key'].startswith('OSName')):
                OSName = instanceTags[i]['Value']

        print("OS Name: " + OSName)
        return OSName

    except Exception as e:
        print("Error getOSName() - ",e)
        print("Error caught, taking default value for OSName : ''")
        return ''


def linux_document_name():
    print("linux_document_name() called")
    try:
        Flag = False
        response =ssm_client.list_documents(
            Filters=[
                {'Key': 'Owner','Values': ['Self']},
                {'Key': 'DocumentType','Values': ['Command']},
                {'Key': 'tag:Owner','Values': ['DXC']},
            ],
        )

        for docs in response['DocumentIdentifiers']:
            if (docs['Name'].find('LinuxLevel2Backup') != -1):
                document_name = docs['Name']
                Flag = True

        if Flag:
            print("Document Name for Linux: " + document_name)
            return document_name
        else:
            print("Level 2 backup document for linux instance not found.")
            return None
    
    except Exception as e:
        print("Error linux_document_name() - ",e)
        return None


def levelTwoBackupLinux(instance_id):
    print("levelTwoBackupLinux() called")
    error_status = False
    try:
        snapshotTags, error_status = getTagsLinuxString(instance_id)
        if not error_status:
            OSName = getOSName(instance_id)

            print("Executing Level 2 backup.")
            response = ssm_client.send_command(
                InstanceIds=[
                    instance_id,
                ],
                DocumentName= linux_document_name(),
                Parameters={ 
                    'instanceTags': [snapshotTags],
                    'osName': [OSName]
                },
                CloudWatchOutputConfig={
                    'CloudWatchLogGroupName': log_group_name,
                    'CloudWatchOutputEnabled': True
                },
            )
            print("Command Id: " + response['Command']['CommandId'])
            return (response['Command']['CommandId'])
        else:
            raise Exception(f"Error getTagsLinuxString() - Error while creating tags string for {instance_id}")
    except Exception as e:
        print("Error levelTwoBackupLinux() - ",e)
        print(f"Error caught while trying to execute run command for linux instance {instance_id}. CommandId Not_Known.")
        return 'Not_Known'

def levelTwoBackupWindows(instance_id):
    print("levelTwoBackupWindows() called")
    error_status = False
    try:
        snapshotTags, error_status = getTagsWindowsString(instance_id)
        if not error_status:
            OSName= getOSName(instance_id)
            print("Executing Level 2 backup.")
            response = ssm_client.send_command(
                InstanceIds=[
                    instance_id,
                ],
                DocumentName='AWSEC2-CreateVssSnapshot',
                Parameters={
                    'description': ['Filesystem-consistent snapshot of ' + OSName + ' Volume.'],
                    'ExcludeBootVolume': ['False'],
                    'tags': [snapshotTags]
                },
                CloudWatchOutputConfig={
                    'CloudWatchLogGroupName': log_group_name,
                    'CloudWatchOutputEnabled': True
                },
            )
            print("Command Id: " + response['Command']['CommandId'])
            return (response['Command']['CommandId'])
        else:
            raise Exception(f"Error getTagsWindowsString() - Error while creating tags string for {instance_id}")
    except Exception as e:
        print("Error levelTwoBackupWindows() - ",e)
        print(f"Error caught while trying to execute run command for windows instance {instance_id}. CommandId Not_Known.")
        return 'Not_Known'

def lambda_handler(event, context):
    global task_token,instance_id
        
    print("input recieved to this script - " + str(event))
    task_token = event["token"]
    event = event["Payload"]
    instance_id = event["instance_id"]
    instance = ec2_resource.Instance(instance_id)
    try:
        if instance.platform:
            if(instance.platform.find('win') != -1):
                print("Windows platform.")
                command_id = levelTwoBackupWindows(instance_id)
                platform = "Windows"
            else:
                print("Linux platform.")
                command_id = levelTwoBackupLinux(instance_id)
                platform = "Linux"
        else:
            print("Linux platform.")
            command_id = levelTwoBackupLinux(instance_id)
            platform = "Linux"

        event['command_id'] = command_id
        event['Instance_Platform'] = platform
        return success_token(event,task_token)
    
    except Exception as e:
        print("Error lambda_handler() - ",e)
        error_status = traceback.format_exc()
        input = {"error" : f"Error lambda_handler() - {str(e)}", "resource_id" : instance_id, "resource_type" : "EC2 Instance"}
        return failure_token(task_token, input, error_status)

#test-case
event = {
  "Flag": "Fix",
  "selfHealJobId": "selfHealJobId_d7a0159d-bae7-11ec-baf7-736e294cbed1",
  "instance_id": "i-03f2a963369545021"
}

if __name__ == "__main__":
    lambda_handler(event,"")