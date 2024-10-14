"""
This Lambda function is used to take event passed as input and decides the value of Resolution_Validation
Logs the same in SelfHeal dynamodb table. 

This Lambda is a part of Selfheal EC2 NativeBackupFailure

In ExecuteBackup state machine (dxcms_sh_nbf_sfn_execute_backup):
gets executed after - ChoiceRecoveryPointCompletion / BackupFailure
On successful check, next state - SendEmail
On FAILURE, next State - TriggerNotificationSfnWError and NotifyForLambaFunctionFailure.
"""


import json
import boto3
import os
import traceback
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))

dynamodb_resource = boto3.resource('dynamodb',config=config)
table_name = os.environ['table_name']

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

def lambda_handler(event, context):
    global task_token,instance_id 
        
    print("input recieved to this script - " + str(event))
    task_token = event["token"]
    event["Payload"]["execution_id"] = event.pop("Execution")
    event["Payload"]["statemachine_name"] = event.pop("StateMachine")
    event = event["Payload"]
    try:
        instance_id = event["instance_id"]
        selfHealJobId = event["selfHealJobId"]
    except:
        instance_id = event["sh_result"]["instance_id"]
        selfHealJobId = event["sh_result"]["selfHealJobId"]
    error_status = False
    try:
        Resolution_Validation = True
        if "backup_validation" in event:
            if event["backup_validation"] == False:
                Resolution_Validation = False
            else:
                event["backup_validation"] = True
        else:
            event["backup_validation"] = True
        if "sh_result" in event:
            sh_result = event.pop("sh_result")
            event = event | sh_result
        
        update_dynamodb(selfHealJobId, "Resolution_Validation", Resolution_Validation)
        update_dynamodb(selfHealJobId, "SelfHealBackupResult", json.dumps(event))
        return success_token(event,task_token)

    except Exception as e:
        print("Error lambda_handler() - ",e)
        if not error_status:
            error_status = traceback.format_exc()
        return failure_token(task_token, str(e)[:200], error_status)

#for updating key and value in a particular dynamodb table
def update_dynamodb(selfHealJobId, attributeKey, attributeValue):
    try:
        print("update_dynamodb() triggered.")
        patch_table = dynamodb_resource.Table(table_name)
        patch_table.update_item(
            Key={'selfHealJobId': selfHealJobId},
            UpdateExpression="set " + attributeKey + "=:data",
            ExpressionAttributeValues={':data': attributeValue},
            ReturnValues="UPDATED_NEW"
        )
    except Exception as e:
        print("Error update_dynamodb() - ",e)
        failure_token(task_token, str(e)[:200], traceback.format_exc())