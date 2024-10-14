"""
    This script is performing 2 tasks:
    1: This check is used to confirm if snapsot is available for the last 24 hours for the EC2 instances with tag value DXCproduct and Backup.
    2: This check is used to confirm if RDS automated snapsot is available for the last 24 hours for the RDS.
    Input Example: {"S3_Bucket":"bucket-for-testing-221", "S3_directory_name":"feature_aws_health_checks/"}
"""
import json
import boto3
import os
import csv
import sys
from datetime import datetime
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))

'''
    Declaration of Global Variables
'''
tag = os.environ['dxcTag']
table_name = os.environ['table_name']
account_Id = boto3.client('sts', config=config).get_caller_identity().get('Account')
account_Name = boto3.client('iam', config=config).list_account_aliases()['AccountAliases'][0]
client = boto3.client('ec2', config=config)
rds_client = boto3.client('rds', config=config)

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

""" this is used to create a attribute key in database """
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
    This function is creating the list of 
    latest EC2 snapshot for each volumes. 
'''
def list_ec2_backup():
    rows = []
    '''
        Collecting information of all the Instances 
        that have a particular tag in it. 
    '''
    try:
        response = client.describe_instances(
            Filters=[{
                'Name': 'tag-key',
                'Values': [tag]
            },],
            DryRun=False
        )
    except:
        print(PrintException())
        exception= print(PrintException())
        put_data("EC2 Client Describe Instances", "List EC2 instance details having particular tag in it", "Error during describeInstances", exception)
        print("Error during describeInstances :(")
    else:
        count = 0
        if len(response["Reservations"]) != 0:
            for reservation in response["Reservations"] :
                for instance in reservation["Instances"]:
                    region = instance['Placement']['AvailabilityZone']
                    instance_id = instance['InstanceId']
                    count = count + 1
                    flag = False
                    print(str(count)+" = "+instance_id)
                    volids = []
                    for devicemaps in instance['BlockDeviceMappings']:
                        ebs = devicemaps['Ebs']
                        volid = ebs['VolumeId']
                        volids.append(volid)
                    print("Attached Volumes: "+str(volids))                      
                    for volume in volids:
                        '''
                            describe_snapshots is use to list all the snapshots for the 
                            particular volume id and to get the creation date and time
                        '''
                        try:
                            response = client.describe_snapshots(
                                Filters=[{
                                    'Name': 'volume-id',
                                    'Values': [str(volume)]
                                },],
                            )                            
                        except:
                            print(PrintException())
                            exception= print(PrintException())
                            put_data("EC2 Client describe_snapshots", "List all snapshots details for particular volume id", "Error during describeSnapshots", exception)
                            print("Error during describeSnapshots")
                        else:                            
                            if len(response['Snapshots']) == 0:
                                result = False
                                latest_snapshot = "-"
                                print("No Snapshot Present")
                            else:
                                i = 0
                                for snapshot in response['Snapshots']:                
                                    result, combined_snapshot_date_time = validate_backup(snapshot['StartTime'])                                    
                                    if i ==0:
                                        i = i+1
                                        latest_snapshot = combined_snapshot_date_time                                        
                                    elif latest_snapshot < combined_snapshot_date_time:
                                        i = i+1
                                        latest_snapshot = combined_snapshot_date_time                                                                           
                                    if result:
                                        break                               
                            if not(result):
                                flag = True
                            status = 'Yes' if result else 'No'
                            row = [account_Id, account_Name, instance_id, volume, latest_snapshot, status]  
                            rows.append(row)
            if len(rows):
                fields = ['Account Number', 'Account Name', 'Resource Id', 'Volume Id', 'Last Backup', 'Status']
                rows.insert(0, fields)    
        else:
            print("No EC2 Instance Found")
    return rows

'''
    This function is creating the list of 
    latest RDS snapshot for each Instance. 
'''
def list_db_backup():
    rows = []
    try:
        response = rds_client.describe_db_instances()['DBInstances']
    except:
        print(PrintException())
        exception= print(PrintException())
        put_data("RDS Client describe_db_instnances", "Lists all db instances", "Error Occured while listing RDS instances", exception)        
    else:
        if len(response):
            for dbinstance in response:
                    try:
                        snapshots = rds_client.describe_db_snapshots(SnapshotType= 'automated', DBInstanceIdentifier= dbinstance['DBInstanceIdentifier'])
                    except:
                        print(PrintException())
                    else:
                        if len(snapshots['DBSnapshots']):
                            i=0
                            for snapshot in snapshots['DBSnapshots']:                                        
                                result, combined_snapshot_date_time = validate_backup(snapshot['SnapshotCreateTime'])
                                if i ==0:
                                    i = i+1
                                    latest_snapshot = combined_snapshot_date_time                                    
                                elif latest_snapshot < combined_snapshot_date_time:
                                    i = i+1
                                    latest_snapshot = combined_snapshot_date_time
                                if result:
                                    print(snapshot['DBSnapshotIdentifier'])
                                    print(combined_snapshot_date_time)
                            status = 'Yes' if result else 'No'
                            endpoint = dbinstance['Endpoint']['Address']
                            print(endpoint)
                            row = [account_Id, account_Name, endpoint, snapshot['DBSnapshotIdentifier'], latest_snapshot, status]  
                            rows.append(row)                        
                        else:
                            print("Automated Backup not found.")
                            print("DB Instance Name:", dbinstance['DBInstanceIdentifier'])
                            row = [account_Id, account_Name, endpoint, '-', '-', 'No']  
                            rows.append(row)            
            if len(rows):
                fields = ['Account Number', 'Account Name', 'Resource Id', 'Snapshot Name', 'Last Backup', 'Status']
                rows.insert(0, fields)
        else:
            print("Database Instance not found")
    return rows

'''
    This function is validating weather the 
    given snapshot is taken withing 24 Hours 
    or not.
'''
def validate_backup(snapshot_date_time):
    NUMBER_OF_SECONDS = 86400 # seconds in 24 hours

    current_date = datetime.utcnow().date()
    current_time = datetime.utcnow().time().replace(microsecond=0)
    combined_current_date_time = datetime.combine(current_date, current_time)
    snapshot_date = snapshot_date_time.date()
    snapshot_time = snapshot_date_time.time().replace(microsecond=0)
    combined_snapshot_date_time = datetime.combine(snapshot_date, snapshot_time)
    time_difference = combined_current_date_time - combined_snapshot_date_time
    return (time_difference.total_seconds() <= NUMBER_OF_SECONDS), combined_snapshot_date_time

'''
    This function takes file uri and rows that needs 
    to be added and then creates the CSV file for it.
'''
def create_report(filename, rows): 
    print("create_report called")
    try:
        with open(filename, 'w', newline='') as csvfile: 
            csvwriter = csv.writer(csvfile)
            csvwriter.writerows(rows)
    except:
        print(PrintException())
        exception= print(PrintException())
        put_data("create report", "Creates the csv report file", "Error Occured during Report Creation", exception)
        print("Error Occurred during Report Creation")
    else:
        print("Report Created Successfully")

'''
    This function upload the given file uri to 
    the S3 bucket and at particular key location provided.
'''
def upload_report(file_uri, bucket_name, key):
    print("upload_report called")
    try:
        s3 = boto3.resource('s3', config=config)
        s3.meta.client.upload_file(file_uri, bucket_name, key)
    except:
        print("File uri: ", file_uri)
        print("Key: ", key)
        print(PrintException())
        exception= print(PrintException())
        put_data("Upload report", "Upload the given file uri to the s3 bucket", "Error Occured during File Upload", exception)
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

def lambda_handler(event, context):
    # TODO implement
    print("Received Event: ", event)
    global uniqueID
    ec2_backup_filename = "ec2_backup_list.csv"
    db_backup_filename = "rds_backup_list.csv"
    try:
        task_token = event['token']
        event = event["Payload"]
        uniqueID = event["uniqueID"]
        hc_put_key(os.environ['AWS_LAMBDA_FUNCTION_NAME'])
        S3_directory_name = event["S3_directory_name"]+ "aws_service_health_check/"
        uri = "/tmp/"      
        rows_1 = list_ec2_backup()
        if len(rows_1):
            create_report(uri+ec2_backup_filename, rows_1)
            upload_report(uri+ec2_backup_filename, event['S3_Bucket'], S3_directory_name+"aws_health_check_output/"+ ec2_backup_filename)
        rows_2 = list_db_backup()
        if len(rows_2):
            create_report(uri+db_backup_filename, rows_2)
            upload_report(uri+db_backup_filename, event['S3_Bucket'], S3_directory_name+"aws_health_check_output/"+ db_backup_filename)
    except:
        Exception=PrintException()
        print(Exception)
        print("Error Occured")
        put_data(f"{os.environ['AWS_LAMBDA_FUNCTION_NAME']} script", "", "Error Occured", Exception)    
    return token(event, task_token)

if __name__ == "__main__":
    event1 = {"S3_Bucket":"bucket-for-testing-221", "S3_directory_name":"feature_aws_health_checks/"}
    lambda_handler(event1, "")