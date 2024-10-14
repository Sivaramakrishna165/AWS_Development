"""
Triggers the notification step function with the details of the error occurred. 

This Lambda is a part of Selfheal EC2 NativeBackupFailure

In SelfHeal state machine(TriggerNotificationSFNWError),
gets executed after any state which catches an error.

On successful check, next state - NotifyForLambdaFunctionFailure
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
    error = False
    try:
        print("trigger_stepfunction() triggered.")
        response = stepfunction_client.start_execution(
            stateMachineArn = step_func_arn,
            input = json.dumps(event_data)
        )

        print("stepFunction Triggered.")
    except Exception as e:
        print("Error trigger_stepfunction() - ",e)
        error = traceback.format_exc()
    finally:
        return error

def lambda_handler(event, context):
    global task_token, resource_id
    print("input recieved to this script - " + str(event))
    error = False
    task_token = event["token"]
    event = event["Payload"]
    try:
        try:
            if "resource_id" in event["sh_result"]:
                resource_id = event["sh_result"]["resource_id"]
            else:
                resource_id = event["sh_result"]["instance_id"]
        except:
            resource_id = "Not_Known"
        try:    
            AccountId = boto3.client('sts',config=config).get_caller_identity().get('Account')
        except:
            error = traceback.format_exc()
            raise Exception(f"Error while reading AccountId. Incident in Service Now is NOT created for Lambda Anomaly")
        arn_prefix = "arn:aws:states:" + region + ":" + AccountId + ":stateMachine:"
        short_message = f"AWS_SH_NBF {AccountId} {region} | Native Backup for {resource_id} does not exist in last 1440 mins"
        event["errorInfo"] = event["sh_result"].pop("errorInfo")
        long_message = f"SelfHeal NBF Step Function caught error. Ec2 Native Backup Missing. Details : {str(event)}."
        notification_event = {
            "resource_id":resource_id,
            "long_message":long_message,
            "short_message":short_message,
            "account_id":AccountId,
            "Resolution_Validation":False,
            "resource_type": "EC2_Instance"
        }

        error = trigger_stepfunction(notification_event, arn_prefix + "dxcms_sh_sfn_notification")
        if error:
            raise Exception(f"Error while triggering dxcms_sh_sfn_notification step function. Incident in Service Now is NOT created for Ec2 Native Backup Failure")

        return success_token(event,task_token)
    except Exception as e:
        print("Error lambda_handler() - ",e)
        input = {"error": str(e), "resource_id" : resource_id, "resource_type" : "LambdaAnomalyCloudWatchAlarm"}
        if not error:
            error = traceback.format_exc()
        return failure_token(task_token, input, error)
