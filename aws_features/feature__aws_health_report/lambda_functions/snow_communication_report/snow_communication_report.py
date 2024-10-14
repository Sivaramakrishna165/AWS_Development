"""
    This main purpose of the script is to check 
    the connectivity of ServiceNow with aws.
    Input Example: {"S3_Bucket":"bucket-for-testing-221", "S3_directory_name":"feature_aws_health_reports/",
    "uniqueID": "healthCheckJobId_b562daaf-1b1c-11ee-abc5-d73369ebe74a"}
"""
from pip._vendor import requests
import boto3
import csv
import os
import sys
import json
import datetime
from datetime import datetime
from botocore.config import Config
from botocore.exceptions import ClientError
config=Config(retries=dict(max_attempts=10,mode='standard'))

uniqueID = ""
table_name = os.environ['table_name']
customer_region = os.environ['AWS_REGION']

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

""" this is using to create a partion key in databse """
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
        
''' this function is used to check key name is available or it will call function to creat new key '''
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
        print("Unable to find unique ID")
        sys.exit(1)

""" this function will return the exception details in a database """
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
        

"""This function will return the stored secretsmanager credencials """       
def get_secret():
    print("inside get_secret")
    secret_name = "DXC-AWSMS-Offerings-SecretKeys"
    region_name = os.environ['AWS_REGION']

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        # For a list of exceptions thrown, see
        # https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
        raise e

    # Decrypts secret using the associated KMS key.
    secret = get_secret_value_response['SecretString']
    data = json.loads(secret)
    if data['AgnosticAPIUserName'] == ' ' or data['AgnosticAPIPassword'] == ' ' or data['AgnosticAPIURL'] == ' ':
        print("Unable to find the snow credencials")
        sys.exit(1)
    else:
        return data
    
"""This function will return the details of SNOW communication with aws """
def SNOW_connectivity(local_file_uri):
    rows=[]
    try:
        account_id = boto3.client('sts').get_caller_identity().get('Account')
        account_name = boto3.client('iam').list_account_aliases()['AccountAliases'][0]
    except:
        exception = PrintException()
        print(exception)
        put_data("account_detail", "list down accont details", "Failed to list down account details", exception)
 
    try:
        secret = get_secret()
        url = secret['AgnosticAPIURL']
        user = secret['AgnosticAPIUserName']
        pwd = secret['AgnosticAPIPassword']
        
        # Set proper headers
        headers = {"Content-Type":"application/json","Accept":"application/json"}
       # if url == None or user == None or pwd == None:
        
        response = requests.get(url, auth=(user, pwd), headers=headers)
        print(response)
        # Check for HTTP codes other than 200
        if response.status_code == 200:
            print('Response:'+str(response.status_code)+ ' Status:SNOW Connectivity - Success')
            data = 'Successful'
        elif response.status_code==201:
            print('Response:'+str(response.status_code)+ ' Status:Success with no body response')
            data = 'Successful with no body response'
        elif response.status_code==400:
            print('Response:'+str(response.status_code)+ ' Status:Bad Request')
            data = 'Bad Request'
        elif response.status_code==401:
            print('Response:'+str(response.status_code)+ ' Status:Unauthorized')
            data = 'Unauthorized'
        elif response.status_code==403:
            print('Response:'+str(response.status_code)+ ' Status:Forbidden')
            data = 'forbidden'
        elif response.status_code==404:
            print('Response:'+str(response.status_code)+ ' Status:Not found')
            data = 'Not Found'
        elif response.status_code==405:
            print('Response:'+str(response.status_code)+ ' Status:Method not allowed')
            data = 'Method not allowed'
        elif response.status_code==406:
            print('Response:'+str(response.status_code)+ ' Status:Not acceptable')
            data = 'Not acceptable'
        elif response.status_code==415:
            print('Response:'+str(response.status_code)+ ' Status:Unsupported media type')
            data = 'Unsupported media type'
            
        snow_connectivity_resource_id = "snow-"+account_id+"-"+customer_region
        print(snow_connectivity_resource_id)
        row = [account_id,account_name,snow_connectivity_resource_id,data]
        rows.append(row)
        create_SNOW_connectivity_report(local_file_uri, rows)
    except Exception as e:
        print(e)        
        return "SSL_Error"
        
""" This function will create report of SNOW connectivity """       
def create_SNOW_connectivity_report(local_file_uri, rows):
    print("create_SNOW_connectivity_report function called .....")
    try:
        filename = local_file_uri
        fields = ['Account Number', 'Account Name','Resource Id','Status']
        with open(filename, 'w', newline='') as csvfile:
            csvwriter = csv.writer(csvfile) 
            csvwriter.writerow(fields) 
            csvwriter.writerows(rows)
    except:
        exception = PrintException()
        print(exception)
        put_data("create_cost_spike_report", " create report", "Failed to create report", exception)


"""this function is used to upload the the created csv file at s3 bucket """
def upload_SNOW_connectivity_report(file_uri, bucket_name, key):
    print("file is uploading and saving at bucket:",end=' ')
    s3 = boto3.resource('s3', config=config)
    try:
        s3.meta.client.upload_file(file_uri, bucket_name, key)
        print( key)
        return True
    except:
        exception = PrintException()
        print(exception)
        put_data("S3 Bucket", "Upload server_report", "Failed to Upload server_report", exception)
        print("================================")
        print("Unable to upload CSV File:"+ file_uri)
        print("Uri Used: "+ key)
        print("================================")

    return False
    
def token(event, task_token):
    sf = boto3.client('stepfunctions')
    sf_output = json.dumps(event)
    sf_response = sf.send_task_success(
        taskToken=task_token,
        output=str(sf_output)
    )
    return sf_response

def lambda_handler(event,context):
    global uniqueID
    task_token = event['token']
    event = event["Payload"]
    uniqueID = event["uniqueID"]
    hc_get_data(os.environ['AWS_LAMBDA_FUNCTION_NAME'])
    local_file_uri = "/tmp/SNOW_connectivity.csv"
    SNOW_connectivity(local_file_uri)
    file_path = 'aws_service_health_check/aws_health_check_output/snow_connectivity.csv'
    upload_SNOW_connectivity_report(local_file_uri, event["S3_Bucket"], event["S3_directory_name"] + file_path)
    print("Run Successfully")  
    return token(event, task_token)    

if __name__ == "__main__":  
    event1 = {"bucket_name": "bucket-for-testing-us-east-2", "key": "development/SNOW_connectivity.csv",
    "uniqueID": "healthCheckJobId_0e2b7490-eb2e-11ed-9806-f5a58ab3b9fa"}
    lambda_handler(event1, "")