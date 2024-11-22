"""
It is loading the services names into Ft_Anomalydetection_Cost DynamoDB table by taking from definition file.
It doesn't require any input to trigger.
"""
import boto3
from botocore.config import Config
import os
import urllib.parse
import json
import http.client

config=Config(retries=dict(max_attempts=10,mode='standard'))

dynamodb_resource = boto3.resource('dynamodb',config=config)

table_name = os.environ['table_name']
list_services = os.environ['AWSServices']

table = dynamodb_resource.Table(table_name)

def read_ssm_parameter(name):
    ssm_para_client = boto3.client('ssm',config=config)
    response = ssm_para_client.get_parameter(
        Name=name,
    )
    ssm_parameter = response['Parameter']
    ssm_parameter_value = ssm_parameter['Value']
    return ssm_parameter_value

def send_response(request, response, status=None, reason=None):
    if status is not None:
        response['Status'] = status
    if reason is not None:
        response['Reason'] = reason
    if 'ResponseURL' in request and request['ResponseURL']:
        try:
            url = urllib.parse.urlparse(request['ResponseURL'])
            body = json.dumps(response)
            https = http.client.HTTPSConnection(url.hostname)
            https.request('PUT', url.path + '?' + url.query, body)
            print('Response sent successfully')
        except:
            print("Failed to send the response to the provided URL")
    return response

def put_data(ServiceName,CostImpact):
    
    try:
        print("put_data() triggered.")
        item_dict = { 
                'ServiceName': ServiceName,
                'CostImpact': CostImpact
                } 

        response = table.put_item(
        Item= item_dict
            )
    except Exception as e:
        print("Error put_data() - ",e)
        print("Error during table.put_item")


def lambda_handler(event, context):
    try:
        print('Received event is ',event)
        response = {}
        response['Status'] = 'SUCCESS'
        response['Reason'] = 'See the details in CloudWatch Log Stream: ' + context.log_stream_name
        response['PhysicalResourceId'] = context.log_stream_name
        response['StackId'] = event['StackId']
        response['RequestId'] = event['RequestId']
        response['LogicalResourceId'] = event['LogicalResourceId']
        response['NoEcho'] = False
        if event['RequestType'] == 'Create':
            ServiceNames = read_ssm_parameter(list_services)
            services = ServiceNames
            total_services=[]
            for service_name in services.split(","):
                if service_name != "":
                    total_services.append(service_name)
            # ServiceNames = ['AWS Secrets Manager','Amazon Simple Notification Service','Amazon Elastic Compute Cloud - Compute','Amazon Simple Queue Service','Amazon Elastic Container Service','Amazon GuardDuty','Amazon FSx','Amazon Simple Storage Service','AWS Lambda','AWS Config','AWS Directory Service','AmazonCloudWatch']
            CostImpact = '100000'
            for ServiceName in total_services:
                put_data(ServiceName,CostImpact)
        else:
            print("Data is alredy loaded into Dynamodb table in previous version")
        send_response(event, response, status='SUCCESS', reason='Lambda Completed')        
    except Exception as e:
        print("Error lambda_handler() - ",e)
        response['Error'] = str(e)
        send_response(event, response, status='FAILED', reason=str(e))
