"""
    This main purpose of the script is to list 
    all the RDS instance along with its all capacity, used and remaining.
    Input Example: {"S3_Bucket":"bucket-for-testing-221", "S3_directory_name":"feature_aws_health_checks/"}
"""
import boto3
import csv
import os
import sys
import json
from datetime import datetime,timedelta
from botocore.config import Config
config=Config(retries=dict(max_attempts=10,mode='standard'))

uniqueID= ""
table_name = os.environ['table_name']

""" this is to capture printing exception occuring at a line"""
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

""" the function is used for getting account details it will return account_id and account_name"""
def account_detail():
    print("account details are printing...........")
    try:
        account_id = boto3.client('sts', config=config).get_caller_identity().get('Account')
        account_name = boto3.client('iam', config=config).list_account_aliases()['AccountAliases'][0]
        return account_id, account_name
    except:
        exception = PrintException()

        print(exception)
        put_data("account_detail", "list down accont details", "Failed to list down account details", exception)


"""this function is used to upload the the created csv file at s3 bucket """
def upload_file(bucket_name, bucket_key, local_uri):
    print("file is uploading and saving at bucket:",end=' ')
    s3 = boto3.resource('s3', config=config)
    try:
        s3.meta.client.upload_file(local_uri, bucket_name, bucket_key)
        print( bucket_key)
        return True
    except:
        exception = PrintException()
        print(exception)
        put_data("S3 Bucket", "Upload server_report", "Failed to Upload server_report", exception)
        print("================================")
        print("Unable to CSV File:"+ local_uri)
        print("Uri Used: "+ bucket_key)
        print("================================")
    return False

"""this function is creating to a csv file at the specified uri"""
def create_report(local_file_uri, rows,flag):
    filename = local_file_uri
    headers = ['Account Number', 'Account Name', 'Resource Id', 'Capacity(GiB)','Used Capacity(GiB)','Available Capacity(GiB)']
    try:
        with open(filename, 'w', newline='') as csvfile:
            csvwriter = csv.writer(csvfile)
            if flag:
                csvwriter.writerow(headers)
            csvwriter.writerows(rows)

    except:
        exception = PrintException()

        print(exception)
        put_data("create_report", "Create server_report", "Failed to create server_report", exception)

'''this function will return the free storage'''
def RDS_free_storage(database_name):
    cloudwatch = boto3.client('cloudwatch')
    try:
        response = cloudwatch.get_metric_data(
            MetricDataQueries=[
                {
                    'Id': 'fetching_FreeStorageSpace',
                    'MetricStat': {
                        'Metric': {
                            'Namespace': 'AWS/RDS',
                            'MetricName': 'FreeStorageSpace',
                            'Dimensions': [
                            {
                            "Name": "DBInstanceIdentifier",
                                "Value": database_name
                            }
                            ]
                        },
                        'Period': 300,
                        'Stat': 'Minimum',
                    }
                }
            ],
            StartTime=(datetime.now() - timedelta(seconds=30 * 3)).timestamp(),
            EndTime=datetime.now().timestamp(),
            ScanBy='TimestampDescending'
            ) 
        free=response['MetricDataResults'][0]['Values']
        return free[0]
    except:
        exception = PrintException()
        print(exception)
        put_data("RDS_free_storage", "fetch the free storage", "Failed to fetch free storage", exception)

""" this function id defined for fetching RDS Capacity"""
def RDS_capacity(file_loc,account_id,account_name):
    print("RDS_capacity function is calling......")
    flag=True
    empt_list=[]
    client = boto3.client('rds')
    config=Config(retries=dict(max_attempts=10,mode='standard'))
    try:
        response = client.describe_db_instances()
        for RDS_dict in response['DBInstances']:
            RDS_free=round((RDS_free_storage(RDS_dict['DBInstanceIdentifier']))/1.074e+9,2)
            available= round(RDS_dict['AllocatedStorage']-RDS_free,2)
            print(RDS_dict['DBInstanceIdentifier'])
            endpoint = RDS_dict['Endpoint']['Address']
            print(endpoint)
            row = [account_id, account_name, endpoint ,RDS_dict['AllocatedStorage'] ,available,RDS_free]
            print(row)
            empt_list.append(row)
        if empt_list:
            create_report(file_loc, empt_list, flag)
    except:
        exception = PrintException()
        print(exception)
        put_data("RDS_capacity", "fetch the allocated storage", "Failed to fetch allocated storage", exception)
        
def token(event, task_token):
    sf = boto3.client('stepfunctions')
    sf_output = json.dumps(event)

    sf_response = sf.send_task_success(
        taskToken=task_token,
        output=str(sf_output)
    )
    return sf_response

""" this is the main fuction where I call all the defined functions by passing their required parameters""" 
def lambda_handler(event,context):
    print("Event Recived",event)
    try:
        global uniqueID
        task_token = event['token']
        event = event["Payload"]
        uniqueID = event["uniqueID"]
        account_id,account_name=account_detail()
        file_loc = "/tmp/RDS_capacity.csv"
        hc_get_data(os.environ['AWS_LAMBDA_FUNCTION_NAME'])
        RDS_capacity(file_loc,account_id,account_name)
        file_location = "aws_service_health_check/"+"aws_health_check_output/"+"rds_capacity.csv"
        upload_file(event["S3_Bucket"],event["S3_directory_name"]+file_location,file_loc)
    except:
        exception = PrintException()
        print(exception)
        put_data("", "", "Something went wrong", exception)
        print("================================")
        print("Error Occurred.")
        print("================================")
    return token(event, task_token)  

event1 = {"S3_Bucket":"bucket-for-testing-221", "S3_directory_name":"abc def/RDS_capacity.csv", "uniqueID": "vytest"}

if __name__ == "__main__":
    lambda_handler(event1,"")
