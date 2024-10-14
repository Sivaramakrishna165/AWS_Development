"""
    This script is doing load the data into Ft_Dxcms_Anomalydetection_EC2 DynamoDB table
    It doesn't require any input to trigger this lambda
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
alarm_sns_action = os.environ['sns_topic_arn']

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

def put_data(alarm_action,Metric_name,expression,Period,Evalution_period,Data_points,tag_name,bucket):

    table = dynamodb_resource.Table(table_name)
    try:
        print("put_data() triggered.")
        item_dict = { 
                'Metric Name': Metric_name,
                'Period': Period,
                'Evalution Period': Evalution_period,
                'Data Points':Data_points,
                'SNS Topic ARN':alarm_action,
                'Tag Name':tag_name,
                'S3 Bucket':bucket
                } 

        response = table.put_item(
            Item= item_dict
        )
    except Exception as e:
        print("Error put_data() - ",e)
        print("Error during table.put_item")

def ssm_parameter(name):
    result = ""
    try:
        ssm = boto3.client('ssm',config=config)
        response = ssm.get_parameter(
            Name = name,
            WithDecryption=True
        )
        result=response['Parameter']['Value']
    except Exception as e:
        print("error in ssm parameter",e)
    return result


def lambda_handler(event, context):
    try:
        print('Received event - ',event)
        response = {}
        response['Status'] = 'SUCCESS'
        response['Reason'] = 'See the details in CloudWatch Log Stream: ' + context.log_stream_name
        response['PhysicalResourceId'] = context.log_stream_name
        response['StackId'] = event['StackId']
        response['RequestId'] = event['RequestId']
        response['LogicalResourceId'] = event['LogicalResourceId']
        response['NoEcho'] = False
        data_points = 1
        evalution_period = 1
        expression = 'ANOMALY_DETECTION_BAND(m1, 2)'
        metric_names = ['MemoryUtilization','DiskSpaceUtilization']
        tag_name = 'adalarm'
        Period = 300
        # account_id = boto3.client("sts").get_caller_identity()["Account"]
        s3_bucket = "cloudops-anomaly-detection-reports"
        alarm_action = ssm_parameter(alarm_sns_action)
        if event['RequestType'] == 'Create':
            print("Started loading the data into DynamoDb table")
            for metric_name in metric_names:
                put_data(alarm_action,metric_name,expression,Period,evalution_period,data_points,tag_name,s3_bucket)
        # elif event['RequestType'] == 'Update':
        #     print("Started loading the data into DynamoDb table")
        #     for metric_name in metric_names: 
        #         put_data(alarm_action,metric_name,expression,Period,evalution_period,data_points,tag_name,s3_bucket)
        else:
            print("Data is alredy loaded into Dynamodb table in previous version")
        send_response(event, response, status='SUCCESS', reason='Lambda Completed')

    except Exception as e:
        print("Error lambda_handler() - ",e)
        response['Error'] = str(e)
        send_response(event, response, status='FAILED', reason=str(e))