"""
    Updates the diagnosis result in the “Ft_Dxcms_SelfHeal” DynamoDB table at key “SelfHealDiagnosisResult”.
    Updates the value of Resolution_Validation as False because there is no resolution taking place for this usecase.  

    This Lambda is a part of Selfheal Lambda Anomaly Detection.
    In dxcms_sh_lad_sfn_diagnosis state machine(DynamoDbLogging),
    gets executed after LambdaAnomalyFilter step.

    Input event of the lambda function is:
        {
            "Payload": {
                "resource_id": "example_resource_id",
                "selfHealJobId": "selfHealJobId_q1312312"
            },
            "StateMachine":"dxcms_sh_lad_sfn_diagnosis",
            "Execution":"<execution_id>"
        }

    In Diagnosis state machine,
    On successful check, next state - SendEmail is called.
    On FAILURE, trigger TriggerNotificationSfnWError and NotifyForLambdaFunctionFailure.
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
        input = {"error" : str(e), "resource_id" : resource_id, "resource_type" : "LambdaAnomalyCloudWatchAlarm"}
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
    global task_token,resource_id 
        
    print("input recieved to this script - " + str(event))
    task_token = event["token"]
    event["Payload"]["execution_id"] = event.pop("Execution")
    event["Payload"]["statemachine_name"] = event.pop("StateMachine")
    event = event["Payload"]
    resource_id = event["resource_id"]
    selfHealJobId = event["selfHealJobId"]
    error_status = False
    try:
        attributeValue = json.dumps(event)
        attributeKey = "SelfHealDiagnosisResult"
        error_status = update_dynamodb(selfHealJobId,attributeKey, attributeValue)
        if error_status:
            raise Exception(f"Error update_dynamodb() - Error while updating diagnosis result in {table_name} dyanamodb table with selfHealJobId {selfHealJobId}.")
        
        status_attributeValue = False
        status_attributeKey = "Resolution_Validation"
        error_status = update_dynamodb(selfHealJobId,status_attributeKey, status_attributeValue)
        if error_status:
            raise Exception(f"Error update_dynamodb() - Error while updating key 'Resolution_Validation' in {table_name} dyanamodb table with selfHealJobId {selfHealJobId}.")
        
        event["Resolution_Validation"] = False
        return success_token(event,task_token)

    except Exception as e:
        print("Error lambda_handler() - ",e)
        if not error_status:
            error_status = traceback.format_exc()
        input = {"error" : f"Error lambda_handler() - {str(e)}", "resource_id" : resource_id, "resource_type" : "LambdaAnomalyCloudWatchAlarm"}
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