"""
This lambda script used to delete the existing snapshots within 24hrs of backup.
This Lambda is a part of Selfheal ec2 backup failure.
In dxcms_sh_bf_sfn_execute_backup state machine(DeleteExcessSnapshots),
gets executed after DynamodbLogging.

Input event of the lambda function is:
{
    "existing_snapshots" : {"vol-1xxxx":[snap-1xxx, snap-2xxx, ...], "vol-2xxxx":[snap-1qqqq, ...]}, 
    "attached_volumes" : [vol-1xxxx, vol-2xxxx, ...],
}

In execute_backup state machine,
On successful check, next state - Sendemail is called.
On FAILURE, next State DeleteExcessSnapshotsError and then NotifyForLambaFunctionFailure.
"""

import json
import traceback
import boto3
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))

ec2_client = boto3.client('ec2', config=config)
ssm_client = boto3.client('ssm', config=config)
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

def lambda_handler(event, context):
    global task_token,instance_id 
        
    print("input recieved to this script - " + str(event))
    task_token = event["token"]
    event = event["Payload"]
    instance_id = event["instance_id"]
    try:
        existing_snapshots = event.pop("existing_snapshots")
        attached_volumes = event["attached_volumes"]
        deleted_snapshots = []

        if (event["backup_level_taken"] == "2"):        
            for vol in attached_volumes:
                if vol not in event["volume_with_no_snapshot"]:
                    if not existing_snapshots[vol] == []:
                        for snap in existing_snapshots[vol]:
                            if snap not in event["AvailableBackupOutput"].values():
                                ec2_client.delete_snapshot(
                                    SnapshotId=snap,
                                )
                                print(snap + " snapshot deleted.")
                                deleted_snapshots.append(snap)
                    
            
        event["deleted_snapshots"] = deleted_snapshots
        return success_token(event,task_token)
    
    except Exception as e:
        print("Error lambda_handler() - ",e)
        input = {"error" : f"Error lambda_handler() - {str(e)}", "resource_id" : instance_id, "resource_type" : "EC2 Instance"}
        return failure_token(task_token, input, traceback.format_exc())