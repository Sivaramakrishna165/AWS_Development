"""
This Lambda function is used to take event passed as input and logs the required details in dynamodb table. 
Input event of the lambda function is:
{
	"selfHealJobId":"<selfHealJobId>",
}
In Diagnosis state machine,
On successful check,TriggerResolutionSNF is called.
On failure, next state DynamoDbLogging Error and then NotifyForLambaFunctionFailure.
In resolution state machine,
On successful check, next state SendEmail is called.
On failure, next state DynamoDbLOgging Error and then NotifyForLambaFunctionFailure.
"""


import json
import boto3
import os
import traceback
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))

dynamodb_resource = boto3.resource('dynamodb',config=config)
table_name = os.environ['table_name']

#input: event
#first merges 2 dictionary in event list into one, and stores in event_dict, returns event_dict
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

def lambda_handler(event, context):
    global task_token,instance_id 
        
    print("input recieved to this script - " + str(event))
    task_token = event["token"]
    event = event["Payload"]
    if ("instance_id" in event):
        instance_id = event["instance_id"]
        selfHealJobId = event["selfHealJobId"]
    else:
        instance_id = event[0]["instance_id"]
        selfHealJobId = event[0]["selfHealJobId"]
    try:
        event_dict = {}
        event_dict.update(event[0])
        event_dict.update(event[1])
        attributeValue = json.dumps(event_dict)
        attributeKey_reso = "SelfHealResolutionResult"
        attributeValue_reso = ""
        
        #if StateMachine value has 'Diagnosis' keyword, then updates "SelfHealDiagnosisResult" key
        if (event[1]["StateMachine"].find('diagnosis') != -1):
            attributeKey = "SelfHealDiagnosisResult"
            update_dynamodb(selfHealJobId,attributeKey_reso, attributeValue_reso)
        #if StateMachine value has 'Resolution' keyword, then updates "SelfHealResolutionResult"key
        if (event[1]["StateMachine"].find('resolution') != -1):
            attributeKey = "SelfHealResolutionResult"

        update_dynamodb(selfHealJobId,attributeKey, attributeValue)

        Issue_Resolution_Status, error_status = check_Issue_Resolution_Status(event)
        if not error_status:
            event[0]["Issue_Resolution_Status"] = Issue_Resolution_Status
        else:
            raise Exception("Error while checking resolution status.")

        return success_token(event,task_token)

    except Exception as e:
        print("Error lambda_handler() - ",e)
        if not error_status:
            error_status = traceback.format_exc()
        input = {"error" : f"Error lambda_handler() - {str(e)}", "resource_id" : instance_id, "resource_type" : "EC2 Instance"}
        return failure_token(task_token, input, error_status)

#for updating key and value in a particular dynamodb table
def update_dynamodb(selfHealJobId, attributeKey, attributeValue):
    try:
        print("update_dynamodb() triggered.")
        patch_table = dynamodb_resource.Table(table_name)
        patch_table.update_item(
            Key={'selfHealJobId': selfHealJobId},
            UpdateExpression="set " + attributeKey + "=:data",
            ExpressionAttributeValues={':data': attributeValue},
            ReturnValues="UPDATED_NEW"
        )
    except Exception as e:
        print("Error update_dynamodb() - ",e)
        input = {"error" : str(e), "resource_id" : instance_id, "resource_type" : "EC2 Instance"}
        failure_token(task_token, input, traceback.format_exc())


def check_Issue_Resolution_Status(event):
    error_status = False
    try:
        print("check_Issue_Resolution_Status() triggered.")
        if ((event[0]["Instance_Tags_Status"] == "Present") and (event[0]["Instance_IAM_Status"] == "Present") and (event[0]["Instance_SSM_Status"] == "Present") and (event[0]["Instance_CLI_Status"] == "Present")):
            Issue_Resolution_Status = True
        else:
            Issue_Resolution_Status = False
    
        return Issue_Resolution_Status, error_status
    except Exception as e:
        print("Error check_Issue_Resolution_Status() - ",e)
        error_status = traceback.format_exc()
        return "", error_status
               





event = [
  {
    "Flag": "Fix",
    "selfHealJobId": "selfHealJobId_319284a9-ee56-11ec-91d2-9b6125a01fd5",
    "instance_id": "i-03e74d54cd95bc864",
    "Instance_Tags_Status": "Present",
    "Missing_Tags": [],
    "Instance_IAM_Status": "Present",
    "Instance_IAM_Role": "Default_Role",
    "Required_Policies": "Present",
    "Instance_State": "running",
    "Instance_SSM_Status": "Present",
    "SSM_Agent_Version": "3.1.1260.0",
    "SSM_Ping_Status": "Online",
    "Instance_CLI_Status": "Present"
  },
  {
    "Execution": "arn:aws:states:ap-southeast-1:338395754338:execution:dxcms_sh_bf_sfn_resolution:b04a4ca6-7860-46ec-ae0a-6bdfcaa26184",
    "StateMachine": "dxcms_sh_bf_sfn_resolution"
  }
]

if __name__ == "__main__":
    lambda_handler(event,"")