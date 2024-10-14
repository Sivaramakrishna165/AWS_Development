"""
This lambda script used to lists down the volumes attached to an instance and it also lists down snapshots
available for each volume id in last 24 hours.
This Lambda is a part of Selfheal ec2 backup failure.
In dxcms_sh_bf_sfn_execute_backup state machine(ListExcessiveSnapshots)
gets executed after dxcms_sh_bf_sfn_resolution state machine.

Input event of the lambda function is:
{
    "instance_id" : "<instance-id>"
}
In dxcms_sh_bf_sfn_execute_backup state machine 
On successful check, next state choosebackuplevel is called.
On FAILURE, next State ListExcessiveSnapshotsError and then NotifyForLambaFunctionFailure.

"""

import json
import boto3
import traceback
from datetime import datetime, timezone, timedelta
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

def list_existing_snapshots(attached_volumes):
    existing_snapshots = {}
    error_status = False
    try:
        print("list_existing_snapshots() triggered.")
        for vol in attached_volumes:
            snapshots = ec2_client.describe_snapshots(
                Filters=[
                    {
                        'Name': 'volume-id',
                        'Values': [vol,]
                    },
                    {
                        'Name': 'tag-key',
                        'Values': ['snapshotLevel',]
                    },
                ],
            )
            Flag = False
            snap_ids = []
            if not snapshots['Snapshots'] == []:
                for snap in snapshots['Snapshots']:
                        snapshot_id = snap['SnapshotId']
                        snapshot_time = snap['StartTime']

                        min_time = datetime.now(timezone.utc) - timedelta(minutes = 1440)
                        
                        if snapshot_time > min_time:
                            snap_ids.append(snapshot_id)
                            
            existing_snapshots[vol] = snap_ids
            
            print(existing_snapshots)
                
        return existing_snapshots, error_status
    
    except Exception as e:
        print("Error list_existing_snapshots() - ",e)
        error_status = traceback.format_exc()
        return existing_snapshots, error_status

def lambda_handler(event, context):
    global task_token,instance_id 
    print("input recieved to this script - " + str(event))
    task_token = event["token"]
    event = event["Payload"]
    instance_id = event["instance_id"]
    error_status = False
    try:
        attached_volumes, error_status = list_volumes(event["instance_id"])
        if not error_status:
            existing_snapshots, error_status = list_existing_snapshots(attached_volumes)
            if not error_status:
                print ("Existing snapshots are : " + str(existing_snapshots))

                event["attached_volumes"] = attached_volumes
                event["existing_snapshots"] = existing_snapshots
            else:
                raise Exception("Error list_existing_snapshots() - Error while listing out existing snapshot ids in last 24 hrs.")
        else:
            raise Exception("Error list_volumes() - Error while listing out attached EBS Volumes.")

        return success_token(event,task_token)
    except Exception as e:
        print("Error lambda_handler() - ",e)
        if not error_status:
            error_status = traceback.format_exc()
        input = {"error" : f"Error lambda_handler() - {str(e)}", "resource_id" : instance_id, "resource_type" : "EC2 Instance"}
        return failure_token(task_token, input, error_status)