"""
This lambda script takes event passed as input and logs the required 
details in dynamodb table. 
This Lambda is a part of Selfheal ec2 backup failure.
In dxcms_sh_sfn_self_heal_master_sfn state machine(DynamoDBLogging),
gets executed after passing payload as input in sns.

event passed as input is(payload through sns:)
    {
        "InstanceId":"<instance-id>",
        "VolumeIds":[<vol-id>"],
        "LatestBackup":"2022-08-21T12:13:29.864Z",
        "EventDate":"2022-08-22T07:13:40.269Z",
        "Event":"BackupFailure",
        "IncidentPriority":"3",
        "region":"<region>"
    }

In dxcms_sh_sfn_self_heal_master_sfn state machine,
On successful check, next state - choice_to_trigger_diagnosis is called.
On FAILURE, next State DynamoDBLoggingError and then NotifyForLambaFunctionFailure.
"""


import json
import boto3
import os
import traceback
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))

dynamodb_resource = boto3.resource('dynamodb',config=config)
table_name = os.environ['Table_Name']
#table_name = "EC2BackupSelfHeal"

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

#input: event
#first merges 2 dictionary in event list into one, and stores in event_dict, returns event_dict
def lambda_handler(event, context):
    global task_token,instance_id
        
    print("input recieved to this script - " + str(event))
    task_token = event["token"]
    event = event["Payload"]
    instance_id = event["instance_id"]
    error_status = False
    try:
        selfHealJobId = event["selfHealJobId"]
        Backup_Validation_Status = event["Backup_Validation_Status"]
        Issue_Resolution_Status = event["Issue_Resolution_Status"]
        selfheal_output = str(event["AvailableBackupOutput"])
        volume_id = event["attached_volumes"]
        error_status = update_dynamodb(selfHealJobId,"Selfheal_Output", selfheal_output)
        
        if ((Backup_Validation_Status == True) and (Issue_Resolution_Status == True)):
            Resolution_Validation = True
        else:
            Resolution_Validation = False
        
        attributeValue = Resolution_Validation
        
        attributeKey = "Resolution_Validation"

        error_status = update_dynamodb(selfHealJobId,attributeKey, attributeValue)

        error_status = update_dynamodb(selfHealJobId,"Volume ID", volume_id)

        event["Resolution_Validation"] = Resolution_Validation

        print("table_updated")
        return success_token(event,task_token)  
    except Exception as e:
        print("Error lambda_handler() - ",e)
        if not error_status:
            error_status = traceback.format_exc()
        input = {"error" : f"Error lambda_handler() - {str(e)}", "resource_id" : instance_id, "resource_type" : "EC2 Instance"}
        return failure_token(task_token, input, error_status)

#for updating key and value in a particular dynamodb table
def update_dynamodb(selfHealJobId, attributeKey, attributeValue):
    error_status = False
    try:
        print("update_dynamodb() triggered.")
        patch_table = dynamodb_resource.Table(table_name)
        patch_table.update_item(
            Key={'selfHealJobId': selfHealJobId},
            UpdateExpression="set " + attributeKey + "=:data",
            ExpressionAttributeValues={':data': attributeValue},
            ReturnValues="UPDATED_NEW"
        )
        return error_status
    except Exception as e:
        print("Error update_dynamodb() - ",e)
        error_status = traceback.format_exc()
        return error_status




event = {
  "selfHealJobId": "selfHealJobId_2dbc5526-ba38-11ec-ac38-11d2b17269cf",
  "instance_id": "i-03f2a963369545021",
  "SelfHealBackupOutput": {},
  "status": "completed",
  "count": 7,
  "AvailableBackupOutput": {
    "vol-0632a9baa8d6064b2": "snap-01317dbc7b8b4a663",
    "vol-079664afd98e55470": "snap-046bb0478aac797b5",
    "vol-0d395860d21ee8871": "snap-05bb0e66e0746e2d5"
  },
  "Resolution_Validation": True
}

if __name__ == "__main__":
    lambda_handler(event,"")