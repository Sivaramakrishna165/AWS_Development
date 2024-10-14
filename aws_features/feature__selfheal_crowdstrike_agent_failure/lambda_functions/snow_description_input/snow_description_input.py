"""
This lambda script is designed for AWS SelfHeal.
This script creates a formatted short and long description, which is passed to create_snow_event script
through event.

Input event of the lambda function is:
{
	"selfHealJobId":"<selfHealJobId>",
}
On successful check, next state TriggerNotificationSNF.
on failure, next state TriggerNotificationSNFError and then NotifyForLambaFunctionFailure.
"""

import json
import boto3
import os
import traceback
from botocore.config import Config

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

        return response
    except Exception as e:
        print("Error read_ddb_table() - ",e)
        input = {"error" : str(e), "resource_id" : instance_id, "resource_type" : "EC2 Instance"}
        failure_token(task_token, input, traceback.format_exc())

def compile_data(event):
    try:
        print("compile_data() triggered.")
        db_table_res = read_ddb_table(event)

        account_id = db_table_res['Item']['AccountId']['S']
        selfheal_result = json.loads(db_table_res['Item']['SelfHealResolutionResult']['S'])
        AccountName = boto3.client('iam',config=config).list_account_aliases()['AccountAliases'][0]
        falcon_agent_status = selfheal_result["falcon_agent_status"]

        selfheal_result.pop('Execution')
        selfheal_result.pop('StateMachine')
        selfheal_result['DynamoDB_Table'] = table_name

        if(falcon_agent_status == "installed_running"):
            short_message = "AWS_SH_CS " + AccountName + " " + region + " | " + "CrowdStrike/Falcon Agent for " + event['instance_id'] + " is now installed"
        else:
            short_message = "AWS_SH_CS " + AccountName + " " + region + " | " + "CrowdStrike/Falcon Agent is NOT installed for " + event['instance_id'] + "."

        # long_message = f'SelfHeal Data : {str(selfheal_result)}. For more details, refer {table_name} dynamoDB table with selfHealJobId as partition key.'
        long_message = str(selfheal_result)

        print(long_message)
        print(short_message)

        return long_message, short_message, account_id
    except Exception as e:
        print("Error compile_data() - ",e)
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
        event1 = event[0]

        long_message, short_message, account_id = compile_data(event1)
        
        event[0]["long_message"] = json.dumps(long_message)
        event[0]["short_message"] = short_message
        event[0]["account_id"] = account_id
        event[0]["resource_type"] = "AWS::EC2::Instance"
        
        return success_token(event,task_token)
    except Exception as e:
        print("Error lambda_handler() - ",e)
        input = {"error" : str(e), "resource_id" : instance_id, "resource_type" : "EC2 Instance"}
        return failure_token(task_token, input, traceback.format_exc())