import uuid
import boto3
import json

def generate_unique_executionId():
    print("generate_uniqueId called")
    execution_id = "SFN_Name_" + str(uuid.uuid1())
    return execution_id

def token(event, task_token):

    sf = boto3.client('stepfunctions')
    sf_output = json.dumps(event)
    # task_token = event['token']

    sf_response = sf.send_task_success(
        taskToken=task_token,
        output=str(sf_output)
    )

    return sf_response

def lambda_handler(event,context):
    task_token = event['token']
    event = event["Payload"]
    
    name = str(generate_unique_executionId())
    
    event['SubSFName'] = name
    return token(event, task_token)
    # return event


# simple test cases
if __name__ == "__main__":
    event1 = {}   
    lambda_handler(event1, "")