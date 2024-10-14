"""
This Lambda function is used to take event passed as input and logs the required details in dynamodb table. 
Input event of the lambda function is:

This Lambda is a part of Selfheal EC2 NativeBackupFailure

In Diagnosis state machine (dxcms_sh_nbf_sfn_diagnosis):
gets executed after - CheckUnmountedVolumes State
On successful check, next state - TriggerResolutionSFN is called.
On FAILURE, next State - TriggerNotificationSfnWError and NotifyForLambaFunctionFailure.

In Resolution state machine (dxcms_sh_nbf_sfn_resolution):
gets executed after - CLIRemediation
On successful check, next state - TriggerExecuteBackupSFN is called.
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

#input: event
#first merges 2 dictionary in event list into one, and stores in event_dict, returns event_dict
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
    event["Payload"]["execution_id"] = event.pop("ExecutionId")
    event["Payload"]["statemachine_name"] = event.pop("StateMachineName")
    event = event["Payload"]
    instance_id = event["instance_id"]
    selfHealJobId = event["selfHealJobId"]
    try:        
        if (event["statemachine_name"].find('diagnosis') != -1):
            update_dynamodb(selfHealJobId, "SelfHealDiagnosisResult", json.dumps(event))
        else:
            update_dynamodb(selfHealJobId, "SelfHealResolutionResult", json.dumps(event))

        Issue_Resolution_Status, error_status = check_issue_resolution_status(event)
        if not error_status:
            event["issue_resolution_status"] = Issue_Resolution_Status
        else:
            raise Exception("Error while checking resolution status.")
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


def check_issue_resolution_status(event):
    error_status = False
    try:
        print("check_issue_resolution_status() triggered.")
        if ((event["Instance_Tags_Status"] == "Present") and (event["instance_iam_status"] == "present") and (event["Instance_SSM_Status"] == "Present") and (event["Instance_CLI_Status"] == "Present") and (event["backup_iam_status"] == "present")):
            Issue_Resolution_Status = True
        else:
            Issue_Resolution_Status = False
        return Issue_Resolution_Status, error_status
    except Exception as e:
        print("Error check_issue_resolution_status() - ",e)
        error_status = traceback.format_exc()
        return False, error_status