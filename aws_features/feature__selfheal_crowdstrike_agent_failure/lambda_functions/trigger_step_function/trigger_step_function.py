"""
This lambda script is used to trigger the next step function. 
It uses the name of the state machine to check which step function to trigger and passes the appropriate 
event into the next state machine.
"""

import json
import boto3
import os
import traceback
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))

stepfunction_client = boto3.client('stepfunctions',config=config)

region = os.environ['AWS_REGION']
resolution_sfn_name = os.environ['resolution_sfn_name']
notification_sfn_name = os.environ['notification_sfn_name']

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
    try:
        response = stepfunction_client.start_execution(
            stateMachineArn = step_func_arn,
            input = json.dumps(event_data)
        )

        print("stepFunction Triggered.")
    except Exception as e:
        print("Error trigger_stepfunction() - ",e)
        input = {"error" : str(e), "resource_id" : instance_id, "resource_type" : "EC2 Instance"}
        failure_token(task_token, input, traceback.format_exc())

def lambda_handler(event, context):
    global task_token, instance_id
        
    print("input recieved to this script - " + str(event))
    task_token = event["token"]
    event = event["Payload"]
    if ("instance_id" in event):
        instance_id = event["instance_id"]
    else:
        instance_id = event[0]["instance_id"]
    try:
        AccountId = boto3.client('sts',config=config).get_caller_identity().get('Account')
        arn_prefix = "arn:aws:states:" + region + ":" + AccountId + ":stateMachine:"

        if (event[1]["StateMachine"].find('diagnosis') != -1):
            resolution_event = {"Flag":"Fix","selfHealJobId":event[0]["selfHealJobId"],"instance_id":event[0]["instance_id"],"falcon_agent_status":event[0]["falcon_agent_status"]}
            trigger_stepfunction(resolution_event, resolution_sfn_name)
        elif (event[1]["StateMachine"].find('resolution') != -1):
            notification_event = {
                "selfHealJobId":event[0]["selfHealJobId"],
                "instance_id":event[0]["instance_id"],
                "long_message":event[0]["long_message"],
                "short_message":event[0]["short_message"],
                "Resolution_Validation":event[0]["Resolution_Validation"],
                "account_id":event[0]["account_id"],
                "resource_type":event[0]["resource_type"]
                }
            trigger_stepfunction(notification_event, notification_sfn_name)

        return success_token(event,task_token)
        
    except Exception as e:
        print("Error lambda_handler() - ",e)
        input = {"error" : str(e), "resource_id" : instance_id, "resource_type" : "EC2 Instance"}
        return failure_token(task_token, input, traceback.format_exc())