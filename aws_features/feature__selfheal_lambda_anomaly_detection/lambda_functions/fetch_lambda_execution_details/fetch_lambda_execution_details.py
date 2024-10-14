"""
    This Lambda function lists out all the lambda functions present and fetches the following details: 
    Total invocations (invocation_sum), maximum duration (duration_max), minimum duration (duration_min) 
    and average duration (duration_avg) for each lambda function executed in last 20 minutes.
    This lambda also update the DynamoDB table with all the execution details.

    This Lambda is a part of Selfheal Lambda Anomaly Detection.
    In dxcms_sh_lad_sfn_diagnosis state machine(FetchLambdaExecutionDetails),
    gets executed as the starting step

    Input event of the lambda function is:
        {"Payload":{
            "resource_id": "example_resource_id",  
            "selfHealJobId": "selfHealJobId_c7ab6asda"  
            }}

    In Diagnosis state machine,
    On successful check, next state - LambdaAnomalyFilter is called.
    On FAILURE, trigger TriggerNotificationSfnWError and NotifyForLambdaFunctionFailure.
"""

import boto3
import json
import traceback
import os
from botocore.config import Config
from datetime import datetime, timezone, timedelta

config=Config(retries=dict(max_attempts=10,mode='standard'))
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

def update_dynamodb(selfHealJobId, attributeKey, attributeValue):
    error_status = False
    try:
        dynamodb_resource = boto3.resource('dynamodb',config=config)
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

# Retrieve a list of all Lambda functions
def get_lambda_functions():
    print("get_lambda_functions() triggered.")
    error_status = False
    lambda_client = boto3.client('lambda',config=config)
    try:
        lambda_list = []
        response = lambda_client.list_functions()
        for lambda_name in response['Functions']:
            lambda_list.append(lambda_name['FunctionName'])
        
        while 'NextMarker' in response:
            response = lambda_client.list_functions(Marker=response['NextMarker'])
            for lambda_name in response['Functions']:
                lambda_list.append(lambda_name['FunctionName'])
    except Exception as e:
        error_status = traceback.format_exc()
        print("error get_lambda_functions() - ", e)
        lambda_list = []
    finally:
        return lambda_list, error_status
        
# Retrieve metrics for a single Lambda function
def get_lambda_metrics(lambda_function):
    print("get_lambda_metrics() triggered.")
    error_status = False
    cw_client = boto3.client('cloudwatch',config=config)
    try:
        response = cw_client.get_metric_data(
            MetricDataQueries=[
                {
                    'Id': 'm1',
                    'MetricStat': {
                        'Metric': {
                            'Namespace': 'AWS/Lambda',
                            'MetricName': 'Invocations',
                            'Dimensions': [
                                {
                                    'Name': 'FunctionName',
                                    'Value':  lambda_function
                                },
                            ]
                        },
                        'Period': 300,
                        'Stat': 'Sum',
                        'Unit': 'Count'
                    },
                },
                {
                    'Id': 'm2',
                    'MetricStat': {
                        'Metric': {
                            'Namespace': 'AWS/Lambda',
                            'MetricName': 'Duration',
                            'Dimensions': [
                                {
                                    'Name': 'FunctionName',
                                    'Value':  lambda_function
                                },
                            ]
                        },
                        'Period': 300,
                        'Stat': 'Maximum',
                        'Unit': 'Milliseconds'
                    },
                },
                
                {
                    'Id': 'm3',
                    'MetricStat': {
                        'Metric': {
                            'Namespace': 'AWS/Lambda',
                            'MetricName': 'Duration',
                            'Dimensions': [
                                {
                                    'Name': 'FunctionName',
                                    'Value':  lambda_function
                                },
                            ]
                        },
                        'Period': 300,
                        'Stat': 'Minimum',
                        'Unit': 'Milliseconds'
                    },
                },
                {
                    'Id': 'm4',
                    'MetricStat': {
                        'Metric': {
                            'Namespace': 'AWS/Lambda',
                            'MetricName': 'Duration',
                            'Dimensions': [
                                {
                                    'Name': 'FunctionName',
                                    'Value':  lambda_function
                                },
                            ]
                        },
                        'Period': 300,
                        'Stat': 'Average',
                        'Unit': 'Milliseconds'
                    },
                },
            ],
            StartTime = datetime.now(timezone.utc) - timedelta(minutes = 20),
            EndTime = datetime.now(timezone.utc)
        )
        if response['MetricDataResults'][0]['Values']:
            invocation_sum = sum(response['MetricDataResults'][0]['Values'])
            duration_max = max(response['MetricDataResults'][1]['Values'])
            duration_min = min(response['MetricDataResults'][2]['Values'])
            s = 0
            for i in range(len(response['MetricDataResults'][3]['Values'])):
                s = s + (response['MetricDataResults'][3]['Values'][i] * response['MetricDataResults'][0]['Values'][i])
            duration_avg = s / invocation_sum
        else:
            invocation_sum = 0
            duration_max = 0
            duration_min = 0
            duration_avg = 0
            
        lambda_metric = {
            'invocation_sum': invocation_sum,
            'duration_max': duration_max,
            'duration_min': duration_min,
            'duration_avg': duration_avg
        }
        return lambda_metric, error_status
    except Exception as e:
        print("error get_lambda_metrics() - ", e)
        print(f"Failed to retrieve metrics for {lambda_function}: {e}")
        return {}, traceback.format_exc()

def lambda_handler(event, context):
    global task_token, resource_id
    print("Received Event is :",event)
    task_token = event['token']
    event = event["Payload"]
    error_status = False
    resource_id= event["resource_id"]
    selfHealJobId = event["selfHealJobId"]
    lambda_details = {}
    # Retrieve a list of all Lambda functions
    try:
        lambda_list, error_status = get_lambda_functions()
        if not error_status:
            for lambda_fn in lambda_list:
                lambda_metric, error_status = get_lambda_metrics(lambda_fn)
                if not error_status:
                    if lambda_metric['invocation_sum'] != 0 or lambda_metric['duration_max'] != 0 or lambda_metric['duration_min'] != 0:
                        lambda_details[lambda_fn] = lambda_metric
                else:
                    raise Exception(f"error get_lambda_metrics() - error while reading lambda metrics for {lambda_fn}")     
        else:
            raise Exception("error get_lambda_functions() - error while generating list of lambda functions")   

        error_status = update_dynamodb(selfHealJobId,"LambdaExecutionDetails",str(lambda_details))
        event["lambda_execution_details"] = lambda_details
        return success_token(event,task_token)
    except Exception as e:
        print("Error lambda_handler() - ",e)
        if not error_status:
            error_status = traceback.format_exc()
        input = {"error" : f"Error lambda_handler() - {str(e)}", "resource_id" : resource_id, "resource_type" : "LambdaAnomalyCloudWatchAlarm"}
        return failure_token(task_token, input, error_status)
