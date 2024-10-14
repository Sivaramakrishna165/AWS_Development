"""
This lambda script is designed for AWS SelfHeal.
This script creates a formatted short and long description, which is passed to create_snow_event script
through event.

Input event of the lambda function is:
{
	"selfHealJobId":"<selfHealJobId>",
}
On successful check, next state TriggerNotificationSNF is called.
on failure, next state TriggerNotificationSNFError and then NotifyForLambaFunctionFailure.
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

def read_ddb_table(event):
    error_status = False
    try:
        print("read_ddb_table() triggered.")
        selfHealJobId = event['selfHealJobId']

        response = db_client.get_item(
            TableName=table_name,
            Key={
                'selfHealJobId': {
                    'S': selfHealJobId,
                }
            }
        )

        return response, error_status
    except Exception as e:
        print("Error read_ddb_table() - ",e)
        return {}, error_status

def compile_data(event):
    error_status = False
    try:
        print("compile_data() triggered.")
        db_table_res, error_status = read_ddb_table(event)
        if not error_status:
            account_id = db_table_res['Item']['AccountId']['S']
            selfheal_result = json.loads(db_table_res['Item']['SelfHealResolutionResult']['S'])
            AccountName = boto3.client('iam',config=config).list_account_aliases()['AccountAliases'][0]
            latest_cloudwatch_logs = selfheal_result["latest_cloudwatch_logs"]

            selfheal_result.pop('Execution')
            selfheal_result.pop('StateMachine')
            selfheal_result['DynamoDB_Table'] = table_name

            if (latest_cloudwatch_logs == "present"):
                short_message = "AWS_SH_CW " + AccountName + " " + region + " | " + "CloudWatch Logs for " + event['instance_id'] + " are successfully getting generated."
            else:
                short_message = "AWS_SH_CW " + AccountName + " " + region + " | " + "CloudWatch Logs for " + event['instance_id'] + " are missing."

            # long_message =  "SelfHeal Data : " + str(selfheal_result) + ". For more details, refer " + table_name + " dynamoDB table with selfHealJobId as partition key."
            long_message = str(selfheal_result)

            print(long_message)
            print(short_message)
        else:
            raise Exception(f"Error read_ddb_table() - Unable to read dynamodb table {table_name} with selfHealJobId {event['selfHealJobId']}")

        return long_message, short_message, account_id, error_status
    except Exception as e:
        print("Error compile_data() - ",e)
        if not error_status:
            error_status = traceback.format_exc()
        return "", "", "", error_status

def lambda_handler(event, context):
    global task_token, instance_id
        
    print("input recieved to this script - " + str(event))
    task_token = event["token"]
    event = event["Payload"]
    if ("instance_id" in event):
        instance_id = event["instance_id"]
    else:
        instance_id = event[0]["instance_id"]
    error_status = False
    try:
        event1 = event[0]

        long_message, short_message, account_id, error_status = compile_data(event1)
        if not error_status:
            event[0]["long_message"] = json.dumps(long_message)
            event[0]["short_message"] = short_message
            event[0]["account_id"] = account_id
            event[0]["resource_type"] = "AWS::EC2::Instance"
        else:
            raise Exception(f"Error compile_data()/read_ddb_table(). Unable to read dynamodb table {table_name} with {event['selfHealJobId']} and compile data.")        
        return success_token(event,task_token)
    except Exception as e:
        print("Error lambda_handler() - ",e)
        if not error_status:
            error_status = traceback.format_exc()
        input = {"error" : f"Error lambda_handler() - {str(e)}", "resource_id" : instance_id, "resource_type" : "EC2 Instance"}
        return failure_token(task_token, input, error_status)