"""
This lambda function triggers notification step function with all required inputs.
This lambda gets triggered if any of the states in step function catches an error.
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
    global task_token, instance_id
    print("input recieved to this script - " + str(event))
    error = False
    task_token = event["token"]
    event = event["Payload"]
    
    try:
        instance_id = json.loads(event["Error"])["resource_id"]
        try:    
            AccountId = boto3.client('sts',config=config).get_caller_identity().get('Account')
        except:
            error = traceback.format_exc()
            raise Exception(f"Error while reading AccountId. Incident in Service Now is NOT created for {instance_id} cloudwatch agent failure issue.")
        
        arn_prefix = "arn:aws:states:" + region + ":" + AccountId + ":stateMachine:"

        short_message = f"AWS_SH_CW {AccountId} {region} | CloudWatch Logs for {instance_id} ec2 instance are missing."

        long_message = f"SelfHeal CloudWatch Step Function caught error. CW agent failure not resolved. Details : {str(event)}."

        notification_event = {
            "instance_id":instance_id,
            "long_message":long_message,
            "short_message":short_message,
            "account_id":AccountId,
            "Resolution_Validation":False,
            "resource_type":"AWS::EC2::Instance"
        }

        error = trigger_stepfunction(notification_event, arn_prefix + "dxcms_sh_sfn_notification")
        if error:
            raise Exception(f"Error while triggering dxcms_sh_sfn_notification step function. Incident in Service Now is NOT created for {instance_id} cloudwatch logs issue.")

        return success_token(event,task_token)
    except Exception as e:
        print("Error lambda_handler() - ",e)
        input = {"error": str(e), "resource_id" : instance_id, "resource_type" : "EC2 Instance"}
        if not error:
            error = traceback.format_exc()
        return failure_token(task_token, input, error)
