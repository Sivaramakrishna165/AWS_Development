"""
    The main purpose of this script is to list 
    all the EC2 Volumes with their attached status.
    Input Example: {"S3_Bucket":"bucket-for-testing-221", "S3_directory_name":"feature_aws_health_checks/"}
"""

import json
import csv
import boto3
import sys
import os
import uuid
from datetime import datetime
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))
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
    This function is creating 
    new record in dynamoDB 
'''
def hc_put_key(hc_name):

    print("hc_put_key called")
    dynamodb_resource = boto3.resource('dynamodb',config=config)
    table = dynamodb_resource.Table(table_name)
    try:
       response = table.put_item(
        Item={ 
                'AWS_HealthCheck_UUI': uniqueID,
                hc_name : [],
                'health_checks': {}
                    }      
            )
    except:
        print(PrintException())
        print("Error during table.put_item")

'''
    This function is updating the dynamoDB 
    table with the information send to it
'''
def put_data(ResourceName, TaskName, Result, Exception):
    print("put_data called")
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


'''
    This function will return list of all volumes 
    with the status of it as attached or  not.
'''
def get_available_volumes():    
    print("get_available_volumes called")
    ec2 = boto3.resource('ec2', config=config)
    account_id = boto3.client('sts', config=config).get_caller_identity().get('Account')
    account_name = boto3.client('iam', config=config).list_account_aliases()['AccountAliases'][0]
    region = boto3.client('ec2', config=config).meta.region_name
    rows = []
    try:   
        volumes = ec2.volumes.all()
    except:
        Exception=PrintException()
        print(Exception)
        print("Error occurred while getting all Volumes")
        put_data("EC2 Resource", "List all the volumes", "Error occurred while getting all Volumes", Exception)      
    else:
        try:
            for volume in volumes:
                row = [account_id, account_name, volume.id, volume.state]
                rows.append(row)
        except:
            Exception=PrintException()
            print(Exception)
            print("Error occurred while traversing through Volumes")
            put_data("EC2 Resource", "Creates list of volumes with status attached or not", "Error occurred while traversing through Volumes", Exception)
            
    return rows, region

'''
    This function takes file uri and rows that needs 
    to be added and then creates the CSV file for it.
'''
def create_report(filename, rows):
    print("create_report called")
    fields = ['Account Number', 'Account Name', 'Resource Id', 'Volume Status']
    try:
        with open(filename, 'w', newline='') as csvfile: 
            csvwriter = csv.writer(csvfile)
            csvwriter.writerow(fields)
            csvwriter.writerows(rows)
    except:
        Exception=PrintException()
        print(Exception)
        put_data("Volume status report", "Creates CSV report file","Error Occurred during volume Report Creation", Exception)
        print("Error Occurred during Report Creation")
    else:
        print("Report Created Successfully")

'''
    This function upload the given file uri to 
    the S3 bucket and at particular key loacation provided.
'''
def upload_report(file_uri, bucket_name, key):
    print("upload_report called")
    try:
        s3 = boto3.resource('s3', config=config)
        s3.meta.client.upload_file(file_uri, bucket_name, key)
    except:
        print("File uri: ", file_uri)
        print("Key: ", key)
        Exception=PrintException()
        print(Exception)
        put_data("S3 Bucket", "Upload file uri to S3 bucket", "Error Occured during volume report File Upload", Exception)
        print("Error Occured during File Upload")
    else:
        print("File uploaded Successfully")
        print("File Saved at: ", key)
        
        
def token(event, task_token):
    sf = boto3.client('stepfunctions')
    sf_output = json.dumps(event)

    sf_response = sf.send_task_success(
        taskToken=task_token,
        output=str(sf_output)
    )
    return sf_response

def lambda_handler(event,context):
    print("Received Event: ", event)
    try:        
        global uniqueID
        task_token = event['token']
        event = event["Payload"]
        uniqueID = event["uniqueID"]
        hc_put_key(os.environ['AWS_LAMBDA_FUNCTION_NAME'])
        S3_directory_name = event["S3_directory_name"]+ "aws_service_health_check/"
        local_uri = "/tmp/Volume_Status_Report.csv"
        script_name = 'unused_volumes'        
        rows, region = get_available_volumes()
        if rows:
            create_report(local_uri, rows)
            upload_report(local_uri, event['S3_Bucket'], S3_directory_name+"aws_health_check_output/"+ script_name+ '.csv')
        else:
            print("Volume not found")
        return token(event, task_token)
    except:
        Exception=PrintException()
        print(Exception)
        print("Error Occured")
        put_data(f"{os.environ['AWS_LAMBDA_FUNCTION_NAME']} script", "", "Error Occured", Exception)

if __name__ == "__main__":
    event1 = {"S3_Bucket":"bucket-for-testing-221", "S3_directory_name":"feature_aws_health_checks/"}
    lambda_handler(event1, "")