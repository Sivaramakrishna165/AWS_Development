"""

This lambda script used to lists down the snapshot ids created by the trigger_level2_backup lambda script.
This Lambda is a part of Selfheal ec2 backup failure.
In dxcms_sh_bf_sfn_execute_backup state machine(Fetchsnapshotids)
gets executed after checkcmdstatus.

Input event of the lambda function is: 
{
    "command_id":"xxxx-xxxx-xxxx-xxxx", 
    "instance_id":"<instance_id>",
    "run_command_status":"success/failed/cancelled"
}

In dxcms_sh_bf_sfn_execute_backup state machine.
On successful check, next state - waitstate to checksnapshotbackupStatus is called.
On FAILURE, next State FetchsnapshotidsError and then NotifyForLambaFunctionFailure.
"""

import json
import boto3
import os
import re
import traceback
from datetime import datetime, timezone, timedelta
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))

ec2_client = boto3.client('ec2', config=config)
ec2_resource = boto3.resource('ec2', config=config)
log_client = boto3.client('logs', config=config)

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

def list_volumes(instance_id):
    print("list_volumes() triggered")
    vol_attached = []
    error_status = False
    try:
        instance = ec2_resource.Instance(instance_id)

        volume_iterator = instance.volumes.all()

        for vol in volume_iterator:
            vol_attached.append(vol.id)
        
        print("attached volumes: " + str(vol_attached))
        return vol_attached, error_status
    
    except Exception as e:
        print("Error list_volumes() - ",e)
        error_status = traceback.format_exc()
        return [], error_status

def get_windows_snapshotIds(event):
    error_status = False
    try:
        print("get_windows_snapshotIds() triggered")
        log_stream_name = event['command_id'] + "/" + event['instance_id'] + "/" + 'runPowerShellScript/stdout'

        response = log_client.get_log_events(
            logGroupName=log_group_name,
            logStreamName= log_stream_name,
            startFromHead=True
        )

        snapshot_ids = {}
        for events in response['events']:
            if (events['message'].find('snap-') != -1):
                pattern = r'({.*"VssSnapshotSetId":"{[^}]+}"})'
                match = re.search(pattern, events['message'])
                if match:
                    json_data = match.group(1)
                    d = json.loads(json_data)
                    for snap in d['Snapshots']:
                        snapshot_ids[snap['EbsVolumeId']] = snap['SnapshotId']
                    if snapshot_ids:
                        break

        print("Snapshots created: " + str(snapshot_ids))
        return snapshot_ids, error_status

    except Exception as e:
        print("Error get_windows_snapshotIds() - ",e)
        error_status = traceback.format_exc()
        return [], error_status

def get_linux_snapshotIds(event):
    error_status = False
    try:
        print("get_linux_snapshotIds() triggered")
        instance = ec2_resource.Instance(event['instance_id'])
        volume_iterator = instance.volumes.all()
        snapshot_ids = {}
        for vol in volume_iterator:
            snapshots = ec2_client.describe_snapshots(
                Filters=[
                    {
                        'Name': 'volume-id',
                        'Values': [vol.id,]
                    },
                ],
            )
            Flag = False
            if not snapshots['Snapshots'] == []:
                for snap in snapshots['Snapshots']:
                    snapshot_id = snap['SnapshotId']
                    snapshot_time = snap['StartTime']
                    
                    min_time = datetime.now(timezone.utc) - timedelta(minutes = 20)
                    
                    if snapshot_time > min_time:
                        if 'Tags' in snap:
                            for i in range(0,len(snap['Tags'])):
                                if(snap['Tags'][i]['Key'] == 'snapshotLevel'):
                                    if (snap['Tags'][i]['Value'] == 'level2'):
                                        snapshot_ids[vol.id] = snapshot_id
                                        Flag = True
                    if Flag == True:
                        break

        print("Snapshots created: " + str(snapshot_ids))
        return snapshot_ids, error_status

    except Exception as e:
        print("Error get_linux_snapshotIds() - ",e)
        error_status = traceback.format_exc()
        return [], error_status

def lambda_handler(event, context):
    global task_token,instance_id
        
    print("input recieved to this script - " + str(event))
    task_token = event["token"]
    event = event["Payload"]
    instance_id = event["instance_id"]
    error_status = False
    try:
        volumes, error_status = list_volumes(event["instance_id"])
        if not error_status:
            instance = ec2_resource.Instance(event["instance_id"])

            if (event['run_command_status'] == 'success'):
                if instance.platform:
                    if(instance.platform.find('win') != -1):
                        snapshot_ids, error_status = get_windows_snapshotIds(event)
                    else:
                        snapshot_ids, error_status = get_linux_snapshotIds(event)
                else:
                    snapshot_ids, error_status = get_linux_snapshotIds(event)

                if not error_status:
                    if snapshot_ids:
                        for vol in volumes:
                            if vol in snapshot_ids.keys():
                                pass
                            else:
                                print("Snapshot not created for volume - " + vol)
                                snapshot_ids[vol] = ''

                        event["SelfHealBackupOutput"] = snapshot_ids
                        event["count"] = 8
                    else:
                        print("can not retreive snapshot ids")
                        event["SelfHealBackupOutput"] = None
                        event["count"] = 8
                else:
                    raise Exception(f"Error while trying to retreive recently created snapshotIds for {instance_id}")
        else:
            raise Exception("Error list_volumes() - Error while listing out attached EBS Volumes.")

        event["backup_level_taken"] = "2"
        event["status"] = "pending"
        return success_token(event,task_token)
        
    except Exception as e:
        print("Error lambda_handler() - ",e)
        if not error_status:
            error_status = traceback.format_exc()
        input = {"error" : "Error lambda_handler()", "resource_id" : instance_id, "resource_type" : "EC2 Instance"}
        return failure_token(task_token, input, error_status)