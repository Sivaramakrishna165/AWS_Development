"""
    The main purpose of this script is to read the JSON file 
    from the S3 Bucket that contains all the command ID and 
    check if it is in Progress then it will return status as 
    True else False.

    Input Example: {"S3_Bucket":"bucket-for-testing-221", "S3_directory_name":"feature_aws_health_checks/", "Count": 8}
"""

import boto3
import json
import sys
import os
from datetime import datetime
from botocore.config import Config



config=Config(retries=dict(max_attempts=10,mode='standard'))


client = boto3.client("ssm", config=config)
s3 = boto3.resource('s3', config=config)

uniqueID = ""
# table_name = "AWS_HealthCheck"
table_name = os.environ['table_name']


'''
    This function will return the Line 
    number and the error that occured.
'''
def PrintException():
    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    captureErr = "Line No. : " + str(lineno)  + " | ERROR: " + str(exc_obj)
    return captureErr


'''
    This function reads the JSON file stored in 
    S3 bucket and creates a list of command ID 
    then returns it.
'''
def custom_json_reader(bucket_name, json_uri):
    print("custom_json_reader Called")
    try:
        content_object = s3.Object(bucket_name, json_uri)
        file_content = content_object.get()['Body'].read().decode('utf-8')
        json_content = json.loads(file_content)
        command_id_list = []
        # print(json_content)
    except:
        exception = PrintException()
        print(exception)
        put_data("S3 Bucket", "Locating JSON config details file", f"Unable to locate File (Key: {json_uri})", exception)
        print("================================")
        print("Unable to get JSON File:"+ json_uri)
        print("Bucket Used: "+bucket_name)
        print("================================")
    
    else:
        try:         
            for platform in json_content:
                # print(platform)
                for health_check_list in json_content[platform]:
                    #print(health_check_list)
                    for health_check_name in health_check_list:
                        #print(health_check_name)
                        # for command_id in health_check_list[health_check_name]:
                        print(f"Platform Name: {platform}  Health Check Name: {health_check_name}  Command ID: {health_check_list[health_check_name]}")
                        command_id_list.append(health_check_list[health_check_name])
        
            if command_id_list:
                return command_id_list
            else:
                print("Command ID List is Empty")
                return []
        
        except:
            exception = PrintException()
            print(exception)
            put_data("S3 Bucket", "Read JSON Config details", f"Unable to read  File (Key: {json_uri})", exception)
            print("================================")
            print("Unable to Traverse JSON Data")
            print("JSON Data: "+str(json_content))
            print("================================")


'''
    This function checks the status of the command ID  
    from the command ID list passed to it and returns True 
    if any of the command ID are in progress else False
'''
def check_commandID_status(command_id_list):

    flag = False
    status = "completed"
    for command_id in command_id_list:
        try:
            response = client.list_command_invocations(
                # CommandId='f504741d-f7cd-4a4b-accb-413820cdce0e'
                CommandId = command_id
                )

        except:
                exception = PrintException()
                print(exception)
                put_data("System Manager", "Check Command ID Status", f"Error Occured during list_command_invocations. Command ID: {str(command_id)}", exception)
                print("================================")
                print("Error Occured during list_command_invocations")
                print("Command ID: "+str(command_id))
                print("================================")

        else:
            for cmdStatus in response['CommandInvocations']:
                print("Command ID: ", cmdStatus['CommandId'])
                print("Instance ID: ", cmdStatus['InstanceId'])
                print("Command Status: ",cmdStatus['Status'])
                if cmdStatus['Status']=="InProgress":
                    status = "pending"
                    flag = True
                    break

            if flag:
                break

    return status


# def put_data(ResourceName, TaskName, Result):

#     print("put_backup_data called")
#     global count
#     count = count + 1
#     now = datetime.now()
#     dynamodb_resource = boto3.resource('dynamodb',config=config)
#     table = dynamodb_resource.Table(table_name)
#     try:
#         response = table.put_item(
#         Item={ 
#                 'AWS_HealthCheck_UUI': uniqueID,
#                 'check_command_id_status' : {
#                     'issue_'+str(count) : {
#                         'ResourceName': ResourceName,
#                         'TaskName': TaskName,
#                         'Result': Result,
#                         'Timestamp': now.strftime("%d/%m/%Y %H:%M:%S")
#                     }
#                 }
#             })
#     except:
#         print(PrintException())
#         print("Error during table.put_item")


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


def token(event, task_token):

    sf = boto3.client('stepfunctions')
    sf_output = json.dumps(event)
    # task_token = event['token']

    sf_response = sf.send_task_success(
        taskToken=task_token,
        output=str(sf_output)
    )

    return sf_response


def lambda_handler(event, context):
    
    print("Received Event: ", event)
    try:
        task_token = event['token']
        event = event["Payload"]

        global uniqueID
        uniqueID = event["uniqueID"]
        hc_get_data(os.environ['AWS_LAMBDA_FUNCTION_NAME'])
        
        json_file_name = 'health_check_config_file.json'
        json_uri = event["S3_directory_name"]+ "inventory/"+json_file_name

        command_id_list =custom_json_reader(event["S3_Bucket"], json_uri)
        if command_id_list:
            event["Status"] = check_commandID_status(command_id_list)
            

    except:
        exception = PrintException()
        print(exception)
        put_data("", "", "", exception)

    Count = event['Count']
    event['Count'] = int(Count) - 1
    return token(event, task_token)


event1 = {
  "uniqueID": "healthCheckJobId_37bdbaac-407e-11ed-9606-77b420fae44b",
  "S3_Bucket": "dxc.338395754338.ap-southeast-1.health-checks",
  "S3_directory_name": "feature_aws_health_checks/", 
  "Count": 8
  }

if __name__ == "__main__":
    lambda_handler(event1,"")