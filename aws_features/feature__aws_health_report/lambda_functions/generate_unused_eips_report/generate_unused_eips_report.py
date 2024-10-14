"""
    The main purpose of this script is to list 
    all the Elastic IPs with there status whether 
    they are in use or not.
    Input Example: {"S3_Bucket":"bucket-for-testing-221", "S3_directory_name":"feature_aws_health_checks/"}
"""
import json
import csv
import boto3
import uuid
import sys
import os
import datetime
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
def hc_get_data(key_name):
    print("hc_get_data called")
    try:
        dynamodb = boto3.resource('dynamodb',config=config)
        table = dynamodb.Table(table_name)
        response = table.get_item(TableName=table_name, Key={'AWS_HealthCheck_UUI':uniqueID})
        if key_name not in response['Item']:
            print(f"Unable to find {key_name} key")
            hc_put_key(key_name)
    except:
        print(PrintException())
        
        
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
    This function list all the Elastic IPs 
    and check if it is free or in-use.
'''
def get_available_elastic_ips():
    print("get_available_elastic_ips called")
    client = boto3.client('ec2', config=config)
    account_id = boto3.client('sts', config=config).get_caller_identity().get('Account')
    account_name = boto3.client('iam', config=config).list_account_aliases()['AccountAliases'][0]
    region = client.meta.region_name
    rows = []
    status = ''
    try:
        addresses_dict = client.describe_addresses()
    except:
        Exception=PrintException()
        print(Exception)
        put_data("EC2 Client Describe Addresses", "Lists all the EIPs ", "Error occurred during describe addersses", Exception)
        print("Error occurred during describe addersses")
    else:
        try:
            for eip_dict in addresses_dict['Addresses']:
                if "NetworkInterfaceId" not in eip_dict:  
                    print(eip_dict['PublicIp'])
                    status = "free"
                else:
                    status = "in-use"                
                row = [account_id, account_name, eip_dict['PublicIp'], status]
                rows.append(row)
        except:
            Exception=PrintException()
            print(Exception)
            put_data("Elastic IPs", "Checks if EIP is free or in-use", "Error occurred while traversing EIP dictionary ", Exception)
    return rows, region

'''
    This function takes file uri and rows that needs 
    to be added and then creates the CSV file for it.
'''
def create_eips_status_report(filename, rows): 
    print("create_eips_status_report called")
    fields = ['Account Number', 'Account Name', 'Resource Id', 'Status']
    try:
        with open(filename, 'w', newline='') as csvfile: 
            csvwriter = csv.writer(csvfile) 
            csvwriter.writerow(fields) 
            csvwriter.writerows(rows)
    except:
        Exception=PrintException()
        print(Exception)
        print("Error Occurred during Report Creation")
        put_data("EIP status report", "Creates CSV report files ", "Error Occurred during EIP Report Creation", Exception)        
    else:
        print("Report Created Successfully")

'''
    This function upload the given file uri to 
    the S3 bucket and at particular key location provided.
'''
def upload_eips_status_report(file_uri, bucket_name, key):
    print("upload_eips_status_report called")
    try:
        s3 = boto3.resource('s3', config=config)
        s3.meta.client.upload_file(file_uri, bucket_name, key)
    except:
        print("File uri: ", file_uri)
        print("Key: ", key)
        Exception=PrintException()
        print(Exception)
        print("Error Occured during File Upload")
        put_data("S3 Bucket", "Upload file uri to S3 bucket", "Error Occured during File Upload to S3 bucket", Exception)        
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

def lambda_handler(event, context):
    # TODO implement
    try:
        global uniqueID
        task_token = event['token']
        event = event["Payload"]
        uniqueID = event["uniqueID"]
        hc_get_data(os.environ['AWS_LAMBDA_FUNCTION_NAME'])        
        S3_directory_name = event["S3_directory_name"]+ "aws_service_health_check/"        
        local_uri = "/tmp/Eips_Status_Report.csv"
        script_name = 'unused_eips'        
        rows, region = get_available_elastic_ips()
        if rows:
            create_eips_status_report(local_uri, rows)
            upload_eips_status_report(local_uri, event['S3_Bucket'], S3_directory_name+"aws_health_check_output/"+ script_name+ '.csv')
        else:
            print("Eips not found")
        return token(event, task_token)
    except:
        Exception=PrintException()
        print(Exception)
        print("Error Occured")
        put_data(f"{os.environ['AWS_LAMBDA_FUNCTION_NAME']} script", "", "Error Occured", Exception)    
    
if __name__ == "__main__":
    event1 = {"S3_Bucket":"bucket-for-testing-221", "S3_directory_name":"feature_aws_health_checks/"}
    lambda_handler(event1, "")