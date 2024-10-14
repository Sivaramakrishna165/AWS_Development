"""
    This main purpose of this script is to list 
    to get report of cost spike as compared to the previous day.
    Input Example: {"S3_Bucket":"bucket-for-testing-221", "S3_directory_name":"feature_aws_health_reports/"}
"""
    
import boto3
import csv
import os
import sys
import json
import datetime
from datetime import datetime
from datetime import date
from datetime import timedelta
from botocore.config import Config

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

""" this is used to create a partion key in database """
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
  
""" This function will list down the last 2 days cost details """
def get_cost_spike_info():
    print("get_cost_spike_info called")
    try:
        account_id = boto3.client('sts').get_caller_identity().get('Account')
        account_name = boto3.client('iam').list_account_aliases()['AccountAliases'][0]
    except:
        exception = PrintException()
        print(exception)
        put_data("account_detail", "list down accont details", "Failed to list down account details", exception)

    try:
        client = boto3.client('ce')
        end_day = date.today()
        start_day = end_day - timedelta(days = 2)
        metric = 'UnblendedCost'
        response = client.get_cost_and_usage(
            TimePeriod={
                'Start': str(start_day),
                'End': str(end_day)
            },
            Granularity='DAILY',
            Metrics=[
                metric,
            ],
            Filter={'Dimensions': {'Key':'REGION','Values': [customer_region] }}
        )
        return response
    except:
        exception = PrintException()
        print(exception)
        put_data("get_cost_spike_info", "list down last two days cost details", "Failed to list down last two days details", exception)

        
""" This function will list down the exact cost spike details along with account details """
def get_cost(local_file_uri):
    print("get_cost called")
    try:
        metric = 'UnblendedCost'
        account_id = boto3.client('sts', config=config).get_caller_identity().get('Account')
        account_name = boto3.client('iam', config=config).list_account_aliases()['AccountAliases'][0]
        Response = get_cost_spike_info()
        rows=[]
        cost_list=[]
        cost_spike_resource_id = "cost-"+account_id+"-"+customer_region
        print(cost_spike_resource_id)
        for item in Response['ResultsByTime']:
            cost_list.append(item['Total']['UnblendedCost']['Amount'])
        unit = item['Total']['UnblendedCost']['Unit']
        if float(cost_list[0]) < float(cost_list[1]):
            row = [account_id,account_name,cost_spike_resource_id,metric,round(float(cost_list[0]),2),round(float(cost_list[1]),2),unit,"spike"]
        else:
            row = [account_id,account_name,cost_spike_resource_id,metric,round(float(cost_list[0]),2),round(float(cost_list[1]),2),unit,"no spike"]
        rows.append(row)
        create_cost_spike_report(local_file_uri, rows)
    except:
        exception = PrintException()
        print(exception)
        put_data("get cost", "list down the cost details", "Failed to list down cost details", exception)
        
        
""" This function will create report of cost spike """        
def create_cost_spike_report(local_file_uri, rows):
    date_list = []
    try:
        Response = get_cost_spike_info()
        for item in Response['ResultsByTime']:
            date_list.append(item['TimePeriod']['Start'])           
        filename = local_file_uri

        fields = ['Account Number', 'Account Name', 'Resource Id','Type', 'Previous Day', 'Current Day' , 'Unit', 'Status',]

        with open(filename, 'w', newline='') as csvfile: 
            csvwriter = csv.writer(csvfile) 
            csvwriter.writerow(fields) 
            csvwriter.writerows(rows)
    except:
        exception = PrintException()
        print(exception)
        put_data("create_cost_spike_report", " create report", "Failed to create report", exception)


"""this function is used to upload the created csv file to an s3 bucket """
def upload_cost_spike_report(file_uri, bucket_name, key):
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
    print("Received Event: ", event)
    try:
        global uniqueID
        task_token = event['token']
        event = event["Payload"]
        uniqueID = event["uniqueID"]
        hc_get_data(os.environ['AWS_LAMBDA_FUNCTION_NAME'])
        local_file_uri = "/tmp/cost-spike.csv"
        get_cost(local_file_uri)
        file_path = 'aws_service_health_check/aws_health_check_output/cost_spike.csv'
        upload_cost_spike_report(local_file_uri, event["S3_Bucket"], event["S3_directory_name"] + file_path)
        print("Run Successfully")
    except:
        exception = PrintException()
        print(exception)
        put_data("", "", "Something went wrong", exception)
        print("================================")
        print("Error Occurred.")
        print("================================")
    return token(event, task_token)

if __name__ == "__main__":  
    event1 = {"bucket_name": "bucket-for-testing-us-east-2", "key": "development/cost-spike.csv",
    "uniqueID": "healthCheckJobId_0e2b7490-eb2e-11ed-9806-f5a58ab3b9fa"}
    lambda_handler(event1, "")