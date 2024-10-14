"""
This Lambda function is used to check the volumes present on an instance is
mounted or not.

In Diagnosis state machine (dxcms_sh_nbf_sfn_diagnosis):
gets executed after - TriggerUnmountedVolCheck then WaitforSSMCmd State
On successful check, next state - DynamoDbLogging is called.
On FAILURE, next State - TriggerNotificationSfnWError and NotifyForLambaFunctionFailure.
"""

import json
import os
import boto3
import re
import traceback
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))

log_client = boto3.client('logs', config=config)
ec2_resource = boto3.resource('ec2', config=config)
ssm_client = boto3.client('ssm', config=config)

# log_group_name = "check_unmounted_volumes_log_group"
log_group_name = os.environ['log_group_name']
windows_document_name = os.environ['windows_document_name']
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

def check_command_status(command_id):
    try:
        print("check_command_status() triggered.")
        response = ssm_client.list_command_invocations(
            CommandId=command_id
        )

        print("Command Status: " + response['CommandInvocations'][0]['Status'])

        return response['CommandInvocations'][0]['Status']
    
    except Exception as e:
        print("Error check_command_status() - ",e)
        return "Not_Known"

def list_volumes(instance_id):
    vol_attached = []
    error_status = False
    try:
        print("list_volumes() triggered.")
        instance = ec2_resource.Instance(instance_id)

        volume_iterator = instance.volumes.all()

        for vol in volume_iterator:
            vol_attached.append(vol.id)
        
        print(f"attached volumes: {vol_attached}")
        return vol_attached, error_status
    
    except Exception as e:
        print("Error list_volumes() - ",e)
        error_status = traceback.format_exc()
        return [], error_status

def list_volume_names(instance_id):
    error_status = False
    vol_names = {}
    try:
        print("list_volume_names() triggered.")
        attached_volumes, error_status = list_volumes(instance_id)
        if not error_status:
            for vol in attached_volumes:
                volume = ec2_resource.Volume(vol)
                name = volume.attachments[0]['Device']
                vol_names[re.sub('[0-9]','',name)] = vol
        else:
            raise Exception("Error list_volumes() - Error listing out attached EBS volumes.")
        
        print(f"volume_name: {vol_names}")
        return attached_volumes,vol_names,error_status
    
    except Exception as e:
        print("Error list_volume_names() - ",e)
        if not error_status:
            error_status = traceback.format_exc()
        return attached_volumes,vol_names,error_status

def linux_unmounted_volumes(command_id, instance_id, attached_volumes, attached_vol_names):
    try:
        print("linux_unmounted_volumes() triggered.")
        log_stream_name =  f"{command_id}/{instance_id}/aws-runShellScript/stdout"
        mounted_disks = []
        # mounted_volumes = []

        response = log_client.get_log_events(
                    logGroupName=log_group_name,
                    logStreamName= log_stream_name,
                    startFromHead=True
                )

        cmd_output = json.loads(response['events'][0]['message'])

        for bd in cmd_output['blockdevices']:
            if bd['mountpoint']:
                mounted_disks.append(bd['name'])
            else:
                if 'children' in bd:
                    for child in bd['children']:
                        if child['mountpoint']:
                            mounted_disks.append(bd['name'])

        mounted_disks = list(set(mounted_disks))
        
        print(f"mounted_disks: {mounted_disks}")
        print(f"attached_vol_names: {attached_vol_names}")

        return mounted_disks

    except Exception as e:
        print("Error linux_unmounted_volumes() - ",e)
        return None

def linux_unmounted_vol_ids(mounted_disks, attached_vol_names, attached_volumes):
    try:
        print("linux_unmounted_vol_ids() triggered.")
        mounted_volumes = []
        for md in mounted_disks:
            if md in attached_vol_names.keys():
                mounted_volumes.append(attached_vol_names[md])

        if (len(mounted_disks) == len(mounted_volumes)):
            unmounted_volume_ids = list(set(attached_volumes) - set(mounted_volumes))
        else:
            attached_vol_short_names = {}
            for key,value in attached_vol_names.items():
                attached_vol_short_names[key[-2:]] = value
            for md in mounted_disks:
                if attached_vol_short_names[md[-2:]] not in mounted_volumes:
                    for disk_names in attached_vol_names.keys():
                        if (md[-2:] == disk_names[-2:]):
                            mounted_volumes.append(attached_vol_short_names[md[-2:]])
            unmounted_volume_ids = list(set(attached_volumes) - set(mounted_volumes))

        print(f"mounted volume ids: {mounted_volumes}")
        print(f"unmounted volume ids: {unmounted_volume_ids}")

        if unmounted_volume_ids:
            return json.dumps(unmounted_volume_ids)
        else:
            return "Not_Known"
    except Exception as e:
        print("Error linux_unmounted_vol_ids() - ",e)
        return "Not_Known"

def windows_unmounted_volumes(command_id, instance_id, attached_volumes):
    try:
        print("windows_unmounted_volumes() triggered.")
        log_stream_name =  f"{command_id}/{instance_id}/runPowerShellScript/stdout"
        print(f"log_stream_name: {log_stream_name}")

        response = log_client.get_log_events(
                    logGroupName=log_group_name,
                    logStreamName= log_stream_name,
                    startFromHead=True
                )
                
        print(f"response message: {response}")

        mounted_vol = []

        for msg in response['events']:
            print(f"msg: {msg}")
            msg_list = str(msg['message']).replace(' ','').split('\n')

            print(f"msg list: {msg_list}")

            for i in msg_list:
                if (i.find('vol-') != -1):
                    mounted_vol.append(i)

        unmounted_volume_ids = list(set(attached_volumes) - set(mounted_vol))

        print(f"mounted volume ids: {mounted_vol}")
        print(f"unmounted volume ids: {unmounted_volume_ids}")

        if unmounted_volume_ids:
            return len(unmounted_volume_ids), json.dumps(unmounted_volume_ids)
        else:
            return 0, "None"
    except Exception as e:
        print("Error windows_unmounted_volumes() - ",e)
        return "Not_Known", "Not_Known"

def lambda_handler(event, context):
    global task_token,instance_id

    error_status = False
    print("input recieved to this script - " + str(event))
    task_token = event["token"]
    event = event["Payload"]
    instance_id = event["instance_id"]
    try:
        command_id = event["mounted_vol_command_id"]
        ssm_status = event["Instance_SSM_Status"]
        attached_volumes, attached_vol_names, error_status = list_volume_names(instance_id)
        if not error_status:
            if (ssm_status == "Present"):
                instance = ec2_resource.Instance(instance_id)

                command_status = check_command_status(command_id)

                if (command_status == 'Success'):
                    if instance.platform:
                        if(instance.platform.find('win') != -1):
                            print("Windows platform.")
                            unmounted_volumes, unmounted_volume_ids = windows_unmounted_volumes(command_id, instance_id, attached_volumes)
                        else:
                            print("Linux platform.")
                            mounted_disks = linux_unmounted_volumes(command_id, instance_id, attached_volumes, attached_vol_names)
                            if mounted_disks != None:
                                unmounted_volumes = len(set(attached_volumes)) - len(set(mounted_disks))
                                if (unmounted_volumes != 0):
                                    unmounted_volume_ids = linux_unmounted_vol_ids(mounted_disks, attached_vol_names, attached_volumes)
                                else:
                                    unmounted_volume_ids = "None"
                            else:
                                unmounted_volumes = "Not_Known"
                                unmounted_volume_ids = "Not_Known"
                    else:
                        print("Linux platform.")
                        mounted_disks = linux_unmounted_volumes(command_id, instance_id, attached_volumes, attached_vol_names)
                        if mounted_disks != None:
                            unmounted_volumes = len(set(attached_volumes)) - len(set(mounted_disks))
                            if (unmounted_volumes != 0):
                                unmounted_volume_ids = linux_unmounted_vol_ids(mounted_disks, attached_vol_names, attached_volumes)
                            else:
                                unmounted_volume_ids = "None"
                        else:
                            unmounted_volumes = "Not_Known"
                            unmounted_volume_ids = "Not_Known"
                else:
                    print("ssm run command failed or not completed yet.")
                    unmounted_volumes = "Not_Known"
                    unmounted_volume_ids = "Not_Known"
            else:
                print("ssm not properly configured.")
                unmounted_volumes = "Not_Known"
                unmounted_volume_ids = "Not_Known"
        else:
            raise Exception("Error list_volume_names() - Error while listing out attached EBS Volumes' names.")
        
        event["attached_volumes"] = json.dumps(attached_volumes)
        event["unmounted_volumes"] = str(unmounted_volumes)
        event["unmounted_volume_ids"] = str(unmounted_volume_ids)
        return success_token(event,task_token)   
    except Exception as e:
        print("Error lambda_handler() - ",e)
        if not error_status:
            error_status = traceback.format_exc()
        return failure_token(task_token, str(e)[:200], error_status)