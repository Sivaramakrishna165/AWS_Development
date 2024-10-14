import boto3
import json
import sys
import os
from datetime import datetime
from botocore.config import Config


config=Config(retries=dict(max_attempts=10, mode='standard'))

uniqueID = ""
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


def copy_s3_data(bucket_name, key):

    print("copy_s3_data called")

    try:
        bucket = s3.Bucket(bucket_name)

        source_key_list = [
                        key + "aws_server_health_check/aws_health_check_processed_data_output/",
                        key + "aws_service_health_check/aws_health_check_processed_output/"
                    ]

        for source_key in source_key_list:

            for object in bucket.objects.filter(Prefix= source_key):
                
                if object.key.endswith("/"):
                    continue

                destination_key = key+ "processed_outputs/"+ str(source_key).split("/")[-3]+ "/"+ str(object.key).split("/")[-1]

                print("Source: "+str(object.key))
                print("Destination :", destination_key)

                copy_s3_object(bucket_name, object.key, destination_key)
        a = "server_list_report"
        source_key = [key+ "inventory/server_list_report.csv",key+ "inventory/service_list_report.csv"]
        for source in source_key:
            print(source)
            if "server" in source:
                destination_key = key+ "processed_outputs/"+ source_key_list[0].split("/")[-3]+ "/server_list_report.csv"
            else:
                destination_key = key+ "processed_outputs/"+ source_key_list[1].split("/")[-3]+ "/service_list_report.csv"
                
            print("Source: ", source)
            print("Destination :", destination_key)
            copy_s3_object(bucket_name, source, destination_key)

    except:
        exception = PrintException()
        print(exception)
        put_data("S3", "Locating Files", f"Failed to locate Files", exception)
        

def copy_s3_object(bucket_name, source_key, destination_key):
    print("copy_s3_object called")
    try:
        copy_source = {
                    'Bucket': bucket_name,
                    'Key': source_key
                }

        s3.meta.client.copy(copy_source, bucket_name, destination_key)
    except:
        exception = PrintException()
        print(exception)
        put_data("S3 Bucket", "Preparing Data for S3 Syncup", f"Failed to prepare Data. Source Key: {source_key},  Destination Key: {destination_key}", exception)


def put_data(ResourceName, TaskName, Result, Exception):
    
    print("put_data called")
    now = datetime.now()
    key_name = os.environ['AWS_LAMBDA_FUNCTION_NAME']
    dynamodb_resource = boto3.resource('dynamodb', config=config)
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

    sf_response = sf.send_task_success(
        taskToken=task_token,
        output=str(sf_output)
    )

    return sf_response


def lambda_handler(event, context):
    # TODO implement  
    print("Event Recieved: ", event)
    try:
        task_token = event['token']
        event = event["Payload"]

        global uniqueID
        uniqueID = event["uniqueID"]
        hc_get_data(os.environ['AWS_LAMBDA_FUNCTION_NAME'])

        copy_s3_data(event["S3_Bucket"], event["S3_directory_name"])
    except:
        exception = PrintException()
        print(exception)
        put_data("", "", "Something went wrong", exception)
    
    #return event
    return token(event, task_token)



if __name__ == "__main__":
    event1 = {
  "S3_Bucket": "dxcms.healthcheck.338395754338.ap-south-1",
  "S3_directory_name": "feature_aws_health_checks/",
  "uniqueID": "healthCheckJobId_6384ccab-4b76-11ed-bdbf-8d7ff2b51705",
  "Status": "pending",
  "Count": 16
}   
    lambda_handler(event1, "")