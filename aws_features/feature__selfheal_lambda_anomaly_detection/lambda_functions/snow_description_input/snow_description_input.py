"""
    Generates long description and short description from the diagnosis result.
    Returns the payload required for creating ServiceNow incident/event, 
    which is to be passed to notification step function. 

    This Lambda is a part of Selfheal Lambda Anomaly Detection.
    In dxcms_sh_lad_sfn_diagnosis state machine(SnowDescriptionInput),
    gets executed after SendEmail step.

    Example Input event of the lambda function is:
        {"Payload":{
            {
                "AlarmName": "<>",
                "NewStateReason": "Thresholds Crossed: 1 out of the last 1 datapoints [17.0 (24/05/23 11:15:00)] was greater than the upper thresholds [15.981390464586445] (minimum 1 datapoint for OK -> ALARM transition).",
                "resource_id": "<>",
                "resource_type": "LambdaAnomalyCloudWatchAlarm",
                "incident_priority": "3",
                "Event Date": "2023-05-25T06:22:50.052Z",
                "Event": "LambdaAnomalyDetection",
                "region": "eu-central-1",
                "account_id": "567529657087",
                "selfHealJobId": "<>",
                "sorted_lambda_execution_details": {
                    "lambda_1_name": {
                    "invocation_sum": 1,
                    "duration_max": 2051.73,
                    "duration_min": 2051.73,
                    "duration_avg": 2051.73
                    },...
                },
                "sorting_filter": "duration_max",
                "execution_id": "<>",
                "statemachine_name": "dxcms_sh_lad_sfn_diagnosis",
                "Resolution_Validation": false
                }
        }}

    In Diagnosis state machine,
    On successful check, next state - TriggerNotificationSFN is called.
    On FAILURE, trigger TriggerNotificationSfnWError and NotifyForLambdaFunctionFailure.
"""

import json
import boto3
import os
from botocore.config import Config
import traceback

config=Config(retries=dict(max_attempts=10,mode='standard'))

db_client = boto3.client('dynamodb',config=config)
ec2_resource = boto3.resource('ec2',config=config)
region = os.environ['AWS_REGION']
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

def compile_data(compile_event):
    error_status = False
    try:
        print("compile_data() triggered.")
        long_message = {"lambda_function_details": compile_event["sorted_lambda_execution_details"]}
        for key in ["sorting_filter","selfHealJobId","account_id","statemachine_name","execution_id", "NewStateReason"]:
            if key in compile_event:
                long_message[key] = compile_event[key]
        long_message['DynamoDB_Table'] = table_name

        try:
            AccountName = boto3.client('iam',config=config).list_account_aliases()['AccountAliases'][0]
            account_id = boto3.client('sts',config=config).get_caller_identity().get('Account')
        except:
            AccountName = compile_event["account_id"]
            account_id = compile_event["account_id"]

        short_message = f"AWS_SH_LAD {account_id} {AccountName} {region} | Lambda Functions Anomaly Detected"

        print(long_message)
        print(short_message)

        return long_message, short_message, error_status
    except Exception as e:
        print("Error compile_data() - ",e)
        if not error_status:
            error_status = traceback.format_exc()
        return "", "", "", error_status

def lambda_handler(event, context):
    global task_token, resource_id
        
    print("input recieved to this script - " + str(event))
    task_token = event["token"]
    event = event["Payload"]
    resource_id = event["resource_id"]
    error_status = False
    try:
        long_message, short_message, error_status = compile_data(event)
        if not error_status:
            new_event = {"notification_sfn_payload":{
                "account_id":event["account_id"], "resource_id":event["resource_id"], "resource_type":"LambdaAnomalyCloudWatchAlarm",
                "Resolution_Validation":False, "selfHealJobId":event["selfHealJobId"],"long_message":long_message,
                "short_message":short_message, "Event":event["Event"], "AlarmName":event["AlarmName"]},
                "statemachine_name":event["statemachine_name"]
                }
        else:
            raise Exception(f"Error compile_data(). Unable to compile data for SNow Incident.")        
        return success_token(new_event,task_token)
    except Exception as e:
        print("Error lambda_handler() - ",e)
        if not error_status:
            error_status = traceback.format_exc()
        input = {"error" : f"Error lambda_handler() - {str(e)}", "resource_id" : resource_id, "resource_type" : "LambdaAnomalyCloudWatchAlarm"}
        return failure_token(task_token, input, error_status)