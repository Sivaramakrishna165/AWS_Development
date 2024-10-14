"""
    The main purpose of this script is to check 
    if there is at least one snapshot available for 
    each volume of EC2 instance
    Input Example: {"S3_Bucket":"bucket-for-testing-221", "S3_directory_name":"feature_aws_health_checks/"}
"""
import boto3
import sys
import os
import uuid
import csv
import json
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

""" this function will return the exception details in a database """
def put_data(ResourceName, TaskName, Result, Exception):    
    print("put_data called")
    now = datetime.now()
    key_name = "generate_server_report"
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
   This function creates the list of all 
   the snapshot with their snapshot count 
   in last 24 hours.
'''
def snapshot_list():
    print("snapshot_list called")
    account_id = boto3.client('sts', config=config).get_caller_identity().get('Account')
    account_name = boto3.client('iam', config=config).list_account_aliases()['AccountAliases'][0]
    region = boto3.client('ec2', config=config).meta.region_name

    rows = []
    volume_count = 0

    ec2 = boto3.resource('ec2', config=config)
    client = boto3.client('ec2', config=config)

    try:
        volumes = ec2.volumes.all()
    except:
        exception= print(PrintException())
        print(PrintException())
        put_data("List Volumes", "List down all the volumes available", "Error during getting volumes", exception)
        print("Error during getting Volumes")
    else:
        current_date = datetime.utcnow().date()
        current_time = datetime.utcnow().time().replace(microsecond=0)
        for volume in volumes:
            volume_count = volume_count+1
            snapshot_count=0
            print(volume.id)
            try:
                snapshots = client.describe_snapshots(
                            Filters=[{
                            'Name': 'volume-id',
                            'Values': [str(volume.id)]
                            },],)
            except:
                exception=print(PrintException())
                print(PrintException())
                put_data("EC2 client describe_snapshots", "List all snapshots for a particular Volume", "Error during describe snapshots", exception)
                
                print("Error during describeSnapshots")
            else:
                try:
                    for snapshot in snapshots['Snapshots']:
                        snapshot_date = snapshot['StartTime'].date()
                        snapshot_time = snapshot['StartTime'].time().replace(microsecond=0)
                        combined_snapshot_date_time = datetime.combine(snapshot_date, snapshot_time)
                        combined_current_date_time = datetime.combine(current_date, current_time)
                        time_difference = combined_current_date_time - combined_snapshot_date_time
                        NUMBER_OF_SECONDS = 86400 # seconds in 24 hours
                        if(time_difference.total_seconds() <= NUMBER_OF_SECONDS): 
                            snapshot_count = snapshot_count + 1
                    row = [account_id, account_name, volume.id, snapshot_count]  
                    rows.append(row)
                except:
                    print(PrintException())
    return rows, region 

'''
    This function takes file uri and rows that needs 
    to be added and then creates the CSV file for it.
'''
def create_report(filename, rows): 
    print("create_report called")
    fields = ['Account Number', 'Account Name', 'Resource Id', 'Snapshot Count']
    try:
        with open(filename, 'w', newline='') as csvfile: 
            csvwriter = csv.writer(csvfile)       
            csvwriter.writerow(fields)       
            csvwriter.writerows(rows)
    except:
        exception= print(PrintException())
        print(PrintException())
        put_data("create report", "Creates the csv report file", "Error Occured during Report Creation", exception)
        print("Error Occurred during Report Creation")
    else:
        print("Report Created Successfully")

'''
    This function upload the given file uri to 
    the S3 bucket and at particular key location provided.
'''
def upload_report(file_uri, bucket_name, key):
    print("Upload_report called")
    try:
        s3 = boto3.resource('s3', config=config)
        s3.meta.client.upload_file(file_uri, bucket_name, key)
    except:
        print("File uri: ", file_uri)
        print("Key: ", key)
        exception= print(PrintException())
        print(PrintException())
        put_data("Upload Report", "Upload the given file uri to the s3 bucket", "Error Occured during File Upload", exception)
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
        local_uri = "/tmp/Snapshot_Count_Report.csv"
        script_name = 'snapshot_count.csv'
        rows, region = snapshot_list()
        if rows:
            create_report(local_uri, rows)
            upload_report(local_uri, event['S3_Bucket'], S3_directory_name+"aws_health_check_output/"+ script_name)
        else:
            print("Snapshots not found")
    except:
        Exception=PrintException()
        print(Exception)
        print("Error Occured")
        put_data(f"{os.environ['AWS_LAMBDA_FUNCTION_NAME']} script", "", "Error Occured", Exception)    
    return token(event, task_token)

if __name__ == "__main__":
    event1 = {"S3_Bucket":"bucket-for-testing-221", "S3_directory_name":"feature_aws_health_checks/"}
    lambda_handler(event1, "")