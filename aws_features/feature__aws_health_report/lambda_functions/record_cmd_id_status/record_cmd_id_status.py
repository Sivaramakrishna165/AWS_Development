import json
import boto3
import os
import sys
from datetime import datetime
from botocore.config import Config


config=Config(retries=dict(max_attempts=10,mode='standard'))


uniqueID = ""
# table_name = "AWS_HealthCheck"
table_name = os.environ['table_name']


def PrintException():
    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    captureErr = "Line No. : " + str(lineno)  + " | ERROR: " + str(exc_obj)
    return captureErr
        
        
# def put_backup_data(uniqueID, instanceID, cmdID, status):

#     print("put_backup_data called")
#     table = dynamodb.Table(table_name)
#     try:
#         response = table.put_item(
#         Item={ 
#                 'AWS_HealthCheck_UUI': str(uniqueID),
#                 'InstanceID/s': str(instanceID),
#                 'Command ID': str(cmdID),
#                 'Status': str(status)         
#                 }    
#             )
#     except:
#         print(PrintException())
#         print("Error during table.put_item")

def hc_put_data(hc_name, ResourceName, TaskName, Result):
    
    print("hc_put_data called")
    now = datetime.now()
    hc_name = hc_name.replace(" ", "_")

    dynamodb_resource = boto3.resource('dynamodb',config=config)
    table = dynamodb_resource.Table(table_name)
    
    try:  
        table.update_item(
        Key={
            'AWS_HealthCheck_UUI': uniqueID},
        UpdateExpression= 'SET health_checks.#hc_name = list_append(health_checks.#hc_name, :obj)',
        ExpressionAttributeNames = { "#hc_name" : hc_name},
        ExpressionAttributeValues={
            ":obj": [
                    {
                        'ResourceName': ResourceName,
                        'TaskName': TaskName,
                        'Result': Result,
                        'Timestamp': now.strftime("%d/%m/%Y %H:%M:%S")
                    }
                ]}
        )
    except:
        print(PrintException())
        print("Error during table.update_item")


def put_data(ResourceName, TaskName, Result, Exception):
    
    print("put_data called")
    # global hc_issue_count
    #issue_count = issue_count + 1
    now = datetime.now()
    key_name = os.environ['AWS_LAMBDA_FUNCTION_NAME']
    dynamodb_resource = boto3.resource('dynamodb',config=config)
    table = dynamodb_resource.Table(table_name)
    
    try:  
        table.update_item(
        Key={
            'AWS_HealthCheck_UUI': uniqueID},
        UpdateExpression= f'SET {key_name} = list_append({key_name}, :obj)',
        ExpressionAttributeValues={
            ":obj": [
                    {
                        'ResourceName': ResourceName,
                        'TaskName': TaskName,
                        'Result': Result,
                        'Exception': Exception,
                        'Timestamp': now.strftime("%d/%m/%Y %H:%M:%S")
                    }
                ]}
        )
    except:
        print(PrintException())
        print("Error during table.update_item")


def hc_get_data(key_name):
    print("hc_get_data called")
    dynamodb = boto3.resource('dynamodb',config=config)
    table = dynamodb.Table(table_name)
    response = table.get_item(TableName=table_name, Key={'AWS_HealthCheck_UUI':uniqueID})
    if key_name not in response['Item']:
        print(f"Unable to find {key_name} key")
        print("Creating...")
        hc_put_key(key_name)


def hc_put_key(hc_name):

    print("hc_put_key called")
    dynamodb_resource = boto3.resource('dynamodb',config=config)
    table = dynamodb_resource.Table(table_name)
    try:
        response = table.update_item(
        Key={
            'AWS_HealthCheck_UUI': uniqueID},
            UpdateExpression=f'SET {hc_name} = :obj',
            ExpressionAttributeValues={":obj": []}
            )
    except:
        print(PrintException())
        print("Error during table.put_item")


def lambda_handler(event, context):
    # TODO implement
    print("Received Event: ", event)
    global uniqueID
    client = boto3.client('ssm', config=config)
    try:
    
        data = json.loads(str(event['Records'][0]['Sns']['Message']))
        # print(type(data))
        print("Data: ",data)

        instance_id = data['instanceId']
        command_id = data["commandId"]
        status = data["status"]

        response = client.list_command_invocations(
                                        CommandId= command_id, 
                                        InstanceId= instance_id
                                    )
        
        print("Response: ",(response["CommandInvocations"][0]["StandardOutputUrl"]).split("/")[5])
        payload_received =  json.loads(((response["CommandInvocations"][0]["StandardOutputUrl"]).split("/")[5]))
        print(f"{payload_received = }")
        
        hc_name = payload_received["health_check"]
        uniqueID = payload_received["uniqueID"]
        hc_get_data(os.environ['AWS_LAMBDA_FUNCTION_NAME'])

        
        hc_put_data(hc_name, f"EC2 Instance:{instance_id}", "Performing Health Check", f"Failed to Perform Health Check. Status: {status}")
        
    except:
        exception = PrintException()
        print(exception)
        put_data("", "", "Something went wrong", exception)
        print("================================")
        print("Error Occurred.")
        print("================================")
    
    # put_backup_data(uniqueID, data["instanceIds"], data["commandId"], data["status"])

    return event


if __name__ == "__main__":
    event1 = {}   

    lambda_handler(event1, "")
