"""
    This Lambda function sorts and returns the lambda functions execution details based on the values 
    of /DXC/SelfHeal/LAD/LambdaSortingFilter SSM parameter.

    This Lambda is a part of Selfheal Lambda Anomaly Detection.
    In dxcms_sh_lad_sfn_diagnosis state machine(LambdaAnomalyFilter),
    gets executed after FetchLambdaExecutionDetails step.

    Input event of the lambda function is:
        {"Payload":{
            "resource_id": "example_resource_id",  
            "lambda_execution_details": {
                "lambda_1_name": {
                    "invocation_sum": 1,
                    "duration_max": 1710.3,
                    "duration_min": 1710.3,
                    "duration_avg": 1710.3
                },
                "lambda_2_name" ...
            }  
        }}

    In Diagnosis state machine,
    On successful check, next state - DynamoDbLogging is called.
    On FAILURE, trigger TriggerNotificationSfnWError and NotifyForLambdaFunctionFailure.
"""

import json
import boto3
import os
import traceback
from collections import OrderedDict
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))
ssm_client = boto3.client('ssm',config=config)

sorting_input_ssm_paramter = os.environ["sorting_input_ssm_paramter"]

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

def read_ssm_parameter():
    error = False
    try:
        print("read_ssm_parameter triggered.")
        ssm_response = ssm_client.get_parameter(
            Name = sorting_input_ssm_paramter
        )
        sorting_literal = ssm_response['Parameter']['Value']
        sorting_literal = sorting_literal.replace("'",'"')
        sorting_dict = json.loads(sorting_literal)
        sorting_filter = sorting_dict["sorting_filter"]
        max_lambdas = int(sorting_dict["max_number_of_lambda_funcs"])
        print(f"sorting_filter is {sorting_filter} and max_number_of_lambda_funcs is {max_lambdas}.")

        return sorting_filter, max_lambdas, error
    
    except Exception as e:
        print("Error read_ssm_parameter() - ",e)
        error = traceback.format_exc()
        return "",-1,error

def lambda_handler(event, context):
    global resource_id, task_token
    print("input recieved to this script - " + str(event))
    task_token = event["token"]
    event = event["Payload"]
    resource_id = event["resource_id"]
    lambda_execution_details = event.pop("lambda_execution_details")
    error_status = False
    try:
        sorting_filter, max_lambdas, error_status = read_ssm_parameter()
        if not error_status:
            sorted_lambda_execution_details = dict(sorted(lambda_execution_details.items(), key=lambda x: x[1][sorting_filter], reverse=True))
            event["sorted_lambda_execution_details"] = OrderedDict(list(sorted_lambda_execution_details.items())[:int(max_lambdas)])
            event["sorting_filter"] = sorting_filter
        else:
            raise Exception(f"Error read_ssm_parameter() - Error while reading value of {sorting_input_ssm_paramter} ssm parameter")
        return success_token(event,task_token)

    except Exception as e:
        print("Error lambda_handler() - ",e)
        if not error_status:
            error_status = traceback.format_exc()
        input = {"error" : f"Error lambda_handler() - {str(e)}", "resource_id" : resource_id, "resource_type" : "LambdaAnomalyCloudWatchAlarm"}
        return failure_token(task_token, input, error_status)