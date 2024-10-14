"""
    The main purpose of this script is to read the 
    Cloud Watch logs and create the CSV file and 
    save it in the S3 bucket.

    Input Example: {"S3_Bucket":"bucket-for-testing-221", "S3_directory_name":"feature_aws_health_checks/"}
"""

from csv import writer
import boto3
import json
import sys
import os
from datetime import datetime
from botocore.config import Config


config=Config(retries=dict(max_attempts=10,mode='standard'))

uniqueID = ""

SSM_CWLogGroupName= os.environ['SSM_CWLogGroupName']    
table_name = os.environ['table_name']
s3 = boto3.resource('s3', config=config)


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
    This function reads the standard output from 
    the cloudwatch logs and than calls the append_csv 
    function with file name and cloud watch logs data.
'''
def cw_logs_reader(output_stream_key, health_check_file_list, health_check_name, instance_id):
    print('bucket_file_reader Called')
    cw_log_client = boto3.client('logs', config=config)
    rows = []
    data1 = []
    try:
        response = cw_log_client.get_log_events(
                        logGroupName=SSM_CWLogGroupName,
                        logStreamName= output_stream_key,
                        startFromHead= False
                        )
        for logs in response['events']:
            data1 = data1 + logs['message'].splitlines()
        if "ERROR - Unable to" in str(data1):
            hc_put_data(health_check_name, f"EC2 Instance:{instance_id}", "Performing Health Check", f"Failed to Perform Health Check. Error: {str(data1)}")
        else:
            if 'windows' in str(health_check_name).lower():
                for item in data1:
                    item = item.split('","')
                    item[0] = str(item[0]).replace('"',"")
                    item[-1] = str(item[-1]).replace('"',"")
                    rows.append(item)
            else:
                for item in data1:
                    rows.append(item.split(','))          
          
            print(health_check_name)
            flag = True
            if health_check_name not in health_check_file_list:

                if os.path.isfile(file_uri+health_check_name+".csv"):
                    os.remove(file_uri+health_check_name+".csv")

                health_check_file_list.append(health_check_name)
                rows[0].insert(0,"Instance_ID")
            else:
                rows[1].insert(0,instance_id)
                rows = rows[1:]
            
            for row in rows:
                if flag:
                    flag = False
                    continue
                row.insert(0,instance_id)    
            append_csv(health_check_name, rows)
        
    except:
        exception = PrintException()
        print(exception)
        put_data("CloudWatch Logs", "Reading Health Check Logs", f"Failed to Read HealthCheck Log. Log Stream Name: {output_stream_key}", exception)
        print("================================")
        print("Unable to find Output File")
        print("Uri Used: "+output_stream_key)
        print("================================")    
    return health_check_file_list
   


'''
    This function append the cloudwatch data to 
    csv name given to it. If file not exist it 
    will create and add data to it. 
'''
def append_csv(file_name, rows):
    print("append_csv Called")    
    try:
        with open(file_uri+file_name+'.csv', 'a', newline='') as f_object:            
            writer_object = writer(f_object)
            for row in rows:
                writer_object.writerow(row)
        
            f_object.close()
    except:
        exception = PrintException()
        print(exception)
        put_data(f"HealthCheck file: {file_name}", "Creating HealthCheck file", "Failed to Create HealthCheck file", exception)
        print("================================")
        print("Unable to write in a File: "+file_name+'.csv')
        print("================================")
        

'''
    This function reads the JSON file from the S3 bucket and 
    then calls bucket_file_reader with those details 
'''
def custom_json_reader(bucket_name, json_uri, csv_key):
    print("custom_json_reader Called")
    health_check_file_list = []
    try:
        content_object = s3.Object(bucket_name, json_uri)
        file_content = content_object.get()['Body'].read().decode('utf-8')
        json_content = json.loads(file_content)
    except:
        exception = PrintException()
        print(exception)
        put_data("S3 Bucket", "Locating JSON Config file", "Failed to JSON Config file", exception)
        print("================================")
        print("Unable to get JSON File:"+ json_uri)
        print("Bucket Used: "+bucket_name)
        print("================================")
    
    else:
        try:         
            for platform in json_content:
                print(platform)
                for health_check_list in json_content[platform]:
                    for health_check_name in health_check_list:
                        print(health_check_list[health_check_name])
                        instance_list = get_instance_list(health_check_list[health_check_name])

                        if instance_list: 
                            for instance_id in instance_list:
                                print(instance_id)
                                key =  health_check_list[health_check_name] +"/"+ instance_id
                                script = "/aws-runPowerShellScript/stdout" if 'windows' in str(platform).lower() else "/aws-runShellScript/stdout"
        
                                health_check_file_list = cw_logs_reader(key+script, health_check_file_list, f"{platform}-{health_check_name}".replace(" ","_"), instance_id)
                        else:
                            print(f"No Instance ID found for {health_check_name} Health Check.")
                            put_data("SSM list_command_invocations", "Reading Instance ID for given Command ID", f"No Instance ID found for Command ID: {health_check_list[health_check_name]}", "")
                                    
            if health_check_file_list:
                upload_csv(health_check_file_list, bucket_name, csv_key)
            else:
                print("Health Check Name List is Empty")
        
        except:
            exception = PrintException()
            print(exception)
            put_data("JSON Config File", "Reading JSON Config data", "Failed to read JSON Config data", exception)
            print("================================")
            print("Unable to Traverse JSON Data")
            print("JSON Data: "+str(json_content))
            print("================================")


def get_instance_list(command_id):

    print("get_instance_list Called")
    instance_list = []
    client = boto3.client('ssm', config=config)
    response = client.list_command_invocations(CommandId= command_id)

    for command_detail in response['CommandInvocations']:
        instance_list.append(command_detail['InstanceId'])
    return instance_list


'''
    This function upload the files from the list to 
    the S3 bucket and at particular key loacation provided.
'''
def upload_csv(health_check_file_list, bucket_name, csv_key):
    print("upload_csv Called")

    for file_name in health_check_file_list:
        try:            
            bucket_uri= f"{csv_key}{file_name}.csv"
            s3.meta.client.upload_file(f"{file_uri}{file_name}.csv", bucket_name,bucket_uri)
        except:
            exception = PrintException()
            print(exception)
            put_data(f"HealthCheck file: {file_name}", "Uploading HealthCheck file", "Failed to Upload HealthCheck file", exception)
            print("================================")
            print("Unable to CSV File:"+ file_name+'.csv')
            print("Uri Used: "+bucket_uri)
            print("================================")
        else:
            print("File Saved at:"+bucket_uri)


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


def delete_bucket_folder(S3_Bucket, S3_directory_name):
    s3 = boto3.resource('s3')
    prefix = "aws_server_health_check/aws_health_check_output/"
    bucket = s3.Bucket(S3_Bucket)
    bucket.objects.filter(Prefix=S3_directory_name+prefix).delete()


def token(event, task_token):

    sf = boto3.client('stepfunctions')
    sf_output = json.dumps(event)
    sf_response = sf.send_task_success(
        taskToken=task_token,
        output=str(sf_output)
    )

    return sf_response


file_uri = "/tmp/"

def lambda_handler(event, context):
    # TODO implement
    print("Received Event: ", event)

    json_file_name = 'health_check_config_file.json'

    try:
        global uniqueID
        task_token = event['token']
        event = event["Payload"]
        uniqueID = event["uniqueID"]
        hc_get_data(os.environ['AWS_LAMBDA_FUNCTION_NAME'])

        delete_bucket_folder(event["S3_Bucket"], event["S3_directory_name"])
        bucket_name = event["S3_Bucket"]
        json_uri = event["S3_directory_name"]+ "inventory/"+ json_file_name
        key = event["S3_directory_name"]+"aws_server_health_check/aws_health_check_output/"
        custom_json_reader(bucket_name, json_uri, key)
    except:
        exception = PrintException()
        print(exception)
        put_data("", "", "Something went wrong", exception)
        print("================================")
        print("Error Occurred.")
        print("================================")        
    
    # return event
    return token(event, task_token)

event1 = {
  "uniqueID": "healthCheckJobId_37bdbaac-407e-11ed-9606-77b420fae44b",
  "S3_Bucket": "dxc.338395754338.ap-southeast-1.health-checks",
  "S3_directory_name": "feature_aws_health_checks/"
  }

if __name__ == "__main__":
    lambda_handler(event1,"")