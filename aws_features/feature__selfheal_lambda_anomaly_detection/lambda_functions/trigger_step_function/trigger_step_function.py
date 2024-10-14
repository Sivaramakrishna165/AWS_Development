"""
    Triggers the notification step function with the required payload needed to create 
    ServiceNow incident / event.  

    This Lambda is a part of Selfheal Lambda Anomaly Detection.
    In dxcms_sh_lad_sfn_diagnosis state machine(TriggerNotificationSFN),
    gets executed after SnowDescriptionInput step.

    Example Input event of the lambda function is:
        {"Payload":{
            "notification_sfn_payload": {
                "resource_id": "<>",
                ...other details..
            },
            "statemachine_name": "dxcms_sh_lad_sfn_diagnosis"
            }
        }

    In Diagnosis state machine,
    On successful check, ends the step function.
    On FAILURE, trigger TriggerNotificationSfnWError and NotifyForLambdaFunctionFailure.
"""

import json
import boto3
import os
import traceback
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))

stepfunction_client = boto3.client('stepfunctions',config=config)

region = os.environ['AWS_REGION']
notification_sfn_arn = os.environ['notification_sfn_arn']

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

def trigger_stepfunction(event_data, step_func_arn):
    error_status = False
    try:
        response = stepfunction_client.start_execution(
            stateMachineArn = step_func_arn,
            input = json.dumps(event_data)
        )

        print("stepFunction Triggered.")
        return error_status
    except Exception as e:
        print("Error trigger_stepfunction() - ",e)
        error_status = traceback.format_exc()
        return error_status

def lambda_handler(event, context):
    global task_token, resource_id
        
    print("input recieved to this script - " + str(event))
    task_token = event["token"]
    event = event["Payload"]
    resource_id = event["notification_sfn_payload"]["resource_id"]
    error_status = False
    try:
        notification_sfn_payload = event["notification_sfn_payload"]
        if (event["statemachine_name"].find('diagnosis') != -1):
            error_status = trigger_stepfunction(notification_sfn_payload, notification_sfn_arn)
            if error_status:
                raise Exception(f"Error trigger_stepfunction(): Error while triggering {notification_sfn_arn} step function.")
        else:
            raise Exception(f"Not a diagnosis sfn. Notification Step Function not triggered.")
        return success_token(event,task_token)
        
    except Exception as e:
        print("Error lambda_handler() - ",e)
        if not error_status:
            error_status = traceback.format_exc()
        input = {"error" : f"Error lambda_handler() - {str(e)}", "resource_id" : resource_id, "resource_type" : "LambdaAnomalyCloudWatchAlarm"}
        return failure_token(task_token, input, error_status)