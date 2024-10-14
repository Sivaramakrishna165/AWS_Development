"""
    This Lambda function is used to check the snapshot of the given snapshot ID is Completed or Not.
    
    This Lambda is a part of Selfheal ec2 backup failure.
    In dxcms_sh_bf_sfn_execute_backup state machine(CheckSnapShotBackupStatus)
    gets executed after FetchsnapshotID's or triggerlevel1backup after waitstate Step.

    Input event of the lambda function is:
    {
        "instance_id": "<instance_id>", 
        "SelfHealBackupOutput":{'vol-0e85bea3f8d1f58f6': 'snap-07e63831713789c75'}, 
        "count": 8, 
        "status": "Pending"
    }

    In dxcms_sh_bf_sfn_execute_backup 
    On successful check, next state - checkstatus is called.
    On FAILURE, next State CheckSnapShotBackupStatusError and then NotifyForLambaFunctionFailure.

"""

import boto3
import sys
import json
import traceback
from botocore.config import Config


config=Config(retries=dict(max_attempts=10,mode='standard'))


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


def check_snapshot_backup_status(event):
    error_status = False
    try:
        print("check_snapshot_backup_status() triggered")
        ec2_client = boto3.client('ec2', config=config)
        if "AvailableBackupOutput" not in event:
            event["AvailableBackupOutput"]= {}

        if "volume_with_no_snapshot" not in event:
            event["volume_with_no_snapshot"]= []

        dict_backup = event["SelfHealBackupOutput"]
        is_empty = not bool(dict_backup)
        
        if(not is_empty):
            for volumeId in list(dict_backup):
                snapshotState = None
                snapshotId = dict_backup[volumeId]
                
                print("Checking status of Snapshot ID : ",snapshotId)
                
                
                try:

                    if not snapshotId == "":

                        responses = ec2_client.describe_snapshots(SnapshotIds=[snapshotId])
                        for response in responses['Snapshots']:
                            snapshotState = response['State']
                        
                        print("snapshotId : ",snapshotId ," | Status : ", snapshotState)
                        
                        if snapshotState == "completed":
                            event["AvailableBackupOutput"].update({volumeId:snapshotId})
                            event["SelfHealBackupOutput"].pop(volumeId)
                    else:
                        event["volume_with_no_snapshot"].append(volumeId)
                        event["SelfHealBackupOutput"].pop(volumeId)
                except Exception as e:
                    # print(PrintException())
                    print("Error check_snapshot_backup_status() - ",e)
                    error_status = traceback.format_exc()
        else:
            event["status"] = "completed"

        return event, error_status
            
    except Exception as e:
        # print(PrintException())
        print("Error check_snapshot_backup_status() - ",e)
        print("Something Went Wrong :(")
        error_status = traceback.format_exc()
        return event, error_status


def lambda_handler(event, context):
    global task_token, instance_id
        
    print("input recieved to this script - " + str(event))
    task_token = event["token"]
    event = event["Payload"]
    instance_id=event["instance_id"]
    error_status = False
    try:
        event, error_status = check_snapshot_backup_status(event)
        if not error_status:
            event["count"] = event["count"] - 1
            # dict_backup = event["SelfHealBackupOutput"]
            # is_empty = not bool(dict_backup)  
            if (event["SelfHealBackupOutput"]) or event["volume_with_no_snapshot"]:
                event["Backup_Validation_Status"] = False
                print(event)

            else:
                if event["backup_level_assigned"] == event["backup_level_taken"]:
                    event["Backup_Validation_Status"] = True
                else:
                    event["Backup_Validation_Status"] = False

            if not (event["SelfHealBackupOutput"]):
                event["status"] = "completed"
        else:
            raise Exception("Error check_snapshot_backup_status() - Error while checking status of snapshots taken.")
        
        return success_token(event,task_token)
    except Exception as e:
        print("Error lambda_handler() - ",e)
        if not error_status:    
            error_status = traceback.format_exc()
        input = {"error" : f"Error lambda_handler() - {str(e)}", "resource_id" : instance_id, "resource_type" : "EC2 Instance"}
        return failure_token(task_token, input, error_status)

# Will be added when backup is available
    # , "AvailableSelfHealBackupOutput":{}


if __name__ == "__main__":
    event1 = {"instance_id": "i-0d5758a7ec1373272", "SelfHealBackupOutput":{'vol-0e85bea3f8d1f58f6': 'snap-07e63831713789c75'}, "count": 8, "status": "Pending"}

    lambda_handler(event1, "")