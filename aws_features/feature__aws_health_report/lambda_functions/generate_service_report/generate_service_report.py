''' 
The main function of this code is to list the "account_number","account_name","technology",
"resource_ID" for all the covered services in healthchecks 
Input Example: {"S3_Bucket":"bucket-for-testing-221", "S3_directory_name":"feature_aws_health_checks/"}
'''
import boto3
import csv
import os
import sys
import uuid
import json
from datetime import datetime
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))
uniqueID= ""
tag = os.environ['dxcTag']
table_name = os.environ['table_name']
customer_region = os.environ['AWS_REGION']
rows = []

""" this is to create printing exception occuring at a line"""
def PrintException():
    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    captureErr = "Line No. : " + str(lineno)  + " | ERROR: " + str(exc_obj)
    return captureErr
    
""" This function is used to generate uniqueID """    
def generate_unique_Id():
    print("generate_uniqueId called")
    execution_id = "healthCheckJobId_" + str(uuid.uuid1())
    return execution_id

""" this is using to create a partion key in database """
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


"""this function is used to upload the the created csv file to s3 bucket """
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

"""this function is creating a csv file at the specified uri"""
def create_report(local_file_uri, rows,flag):
    filename = local_file_uri
    headers = ['account_number', 'account_name', 'technology', 'resource_id']
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

"""this function is listing the eip"""
def unused_ip(resource_type, file_loc,account_id,account_name):
    print("eip is listing down")
    flag=True
    client = boto3.client('ec2',config=config)    
    try:
        addresses_dict = client.describe_addresses()
        for eip_dict in addresses_dict['Addresses']:
            row = [account_id, account_name,resource_type, eip_dict['PublicIp']]
            print(row)
            rows.append(row)
    except:
        exception = PrintException()
        print(exception)
        put_data("unused_ip", "list down eip", "Failed to list down eip", exception)

""" this function is listing volume"""
def unused_volume(resource_type, file_loc, account_id, account_name):
    print("volume is listing...............")
    flag=False
    client = boto3.client('ec2',config=config)
    response = client.describe_volumes()
    try:
        for vol_dict in response['Volumes']:
            row = [account_id, account_name,resource_type, vol_dict['VolumeId']]
            print(row)
            rows.append(row)
    except:
        exception = PrintException()
        print(exception)
        put_data("unused_volume", "list down volume ID", "Failed to list down volume ID", exception)
        
def RDS_capacity(resource_type, file_loc, account_id, account_name):
    print("RDS_capacity function is calling......")
    flag=False
    client = boto3.client('rds')
    config=Config(retries=dict(max_attempts=10,mode='standard'))
    try:
        response = client.describe_db_instances()
        for RDS_dict in response['DBInstances']:
            endpoint = RDS_dict['Endpoint']['Address']
            row = [account_id, account_name,resource_type, endpoint]
            rows.append(row)
    except:
        exception = PrintException()
        print(exception)
        put_data("RDS_capacity", "fetch the allocated storage", "Failed to fetch allocated storage", exception)
        
def cost_spike(resource_type, file_loc, account_id, account_name):
    print("cost_spike function is calling ...............")
    flag=False
    try:
        cost_spike_resource_id = "cost-"+account_id+"-"+customer_region
        print(cost_spike_resource_id)
        row = [account_id, account_name,resource_type, cost_spike_resource_id]
        print(row)
        rows.append(row)
    except:
        exception = PrintException()
        print(exception)
        put_data("cost_spike", "list down cost_spike details", "Failed to list down cost_spike details", exception)
        
def SNOW(resource_type, file_loc, account_id, account_name):
    print("SNOW function is calling ...............")
    flag=False
    try: 
        snow_connectivity_resource_id = "snow-"+account_id+"-"+customer_region
        print(snow_connectivity_resource_id)
        row = [account_id, account_name,resource_type, snow_connectivity_resource_id]
        rows.append(row)
    except:
        exception = PrintException()
        print(exception)
        put_data("SNOW", "list down SNOW details", "Failed to list down SNOW details", exception)
        

"""" this function is used to list snapshot_deletion_tag"""
def snapshot_deletion_tag(resource_type,file_loc, account_id, account_name):
    print("snapshot_deletion_tag function is calling................")
    flag=False
    client = boto3.client('ec2', config=config)
    try:
        snapshots = client.describe_snapshots()
    except:
        print(PrintException())
        print("Error during describeSnapshots")
    else:
        try:
            for snapshot in snapshots['Snapshots']:
                row = [account_id, account_name, resource_type, snapshot['SnapshotId']] 
                rows.append(row)
            create_report(file_loc, rows, flag)
        except:
            exception= PrintException()
            print(exception)
            put_data("snapshot_deletion_tag", "list down snapshot_deletion_tag", "Failed to list down snapshot_deletion_tag", exception)

"""this function is used to list snapshot_count"""
def snapshot_count(resource_type,file_loc, account_id, account_name):
    print("snapshot_count function is calling....................")
    flag=False
    ec2 = boto3.resource('ec2', config=config)
    try:
        volumes = ec2.volumes.all()
    except:
        exception=PrintException()
        print(exception)
        print("Error during getting Snapshot Count")
        put_data("Snapshot count", "list down snapshot count", "Failed to list down snapshot count", exception)
    else:
        for volume in volumes:
            row = [account_id, account_name, resource_type , volume.id]
            rows.append(row)

def list_ec2_backup(resource_type,file_loc,account_id,account_name):
    flag = True
    client = boto3.client('ec2', config=config)
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
                    row = [account_id, account_name,resource_type, instance_id]  
                    print(row)
                    rows.append(row)
                    #create_report(file_loc, rows, flag)
        else:
            print("No EC2 Instance Found")

def token(event, task_token):
    sf = boto3.client('stepfunctions')
    sf_output = json.dumps(event)
    sf_response = sf.send_task_success(
        taskToken=task_token,
        output=str(sf_output)
    )
    return sf_response

def lambda_handler(event,context):
    print("Event Recived",event)
    try:
        task_token = event['token']
        event = event["Payload"]
        global uniqueID
        uniqueID = generate_unique_Id()
        event["uniqueID"] = uniqueID
        account_id,account_name=account_detail()
        file_loc = "/tmp/servicHCinventory.csv"
        hc_put_key(os.environ['AWS_LAMBDA_FUNCTION_NAME'])       
        unused_ip('unused eips',file_loc,account_id,account_name)
        unused_volume('unused volumes',file_loc,account_id,account_name)
        snapshot_count('snapshot count',file_loc,account_id,account_name)
        RDS_capacity('rds capacity',file_loc,account_id,account_name)
        cost_spike('cost spike',file_loc,account_id,account_name)
        SNOW('snow connectivity',file_loc,account_id,account_name)
        RDS_capacity('rds backup list',file_loc,account_id,account_name)
        list_ec2_backup('ec2 backup',file_loc,account_id,account_name)
        snapshot_deletion_tag('snapshot delete tag',file_loc,account_id,account_name)
        #RDS_capacity('rds backup list',file_loc,account_id,account_name)
        #list_ec2_backup('ec2 backup',file_loc,account_id,account_name)
        upload_file(event["S3_Bucket"],event["S3_directory_name"]+ "inventory/" + "service_list_report.csv",file_loc)
        
    except:
        exception = PrintException()
        print(exception)
        put_data("", "", "Something went wrong", exception)
        print("================================")
        print("Error Occurred.")
        print("================================")
       
    return token(event, task_token)
    #return event

#lambda_handler()
event1 = {"S3_Bucket":"bucket-for-testing-221", "S3_directory_name":"abc def/service_inventory.csv"}

if __name__ == "__main__":
    lambda_handler(event1,"")