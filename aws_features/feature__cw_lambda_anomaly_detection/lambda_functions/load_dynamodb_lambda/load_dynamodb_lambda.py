""""
This lambda function is loading the data into Ft_Dxcms_Anomalydetection_Lambda DynamoDB table
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

sns_topic_arn = os.environ['sns_topic_arn']

table_name = os.environ['table_name']

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

def put_data(Metric_name,Period,Evalution_period, Data_points, Band):

    table = dynamodb_resource.Table(table_name)
    try:
        print("put_data() triggered.")
        item_dict = { 
                'Metric Name': Metric_name,
                'Period': Period,
                'Evalution Period': Evalution_period,
                'Data Points':Data_points,
                'Band': Band,
                'SNS Topic ARN':sns_topic_arn
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
        Period = "300"
        Evalution_period = "2"
        Data_points = "2"
        Band = "2"
        if event['RequestType'] == 'Create':
            print("Started loading the data into DynamoDb table")
            metric_names = ['Invocations','Throttles']
            for metric_name in metric_names:
                put_data(metric_name, Period, Evalution_period, Data_points, Band)
        else:
            print("Data is alredy loaded into Dynamodb table in previous version")
        send_response(event, response, status='SUCCESS', reason='Lambda Completed')
        
    except Exception as e:
        print("Error lambda_handler() - ",e)
        response['Error'] = str(e)
        send_response(event, response, status='FAILED', reason=str(e))