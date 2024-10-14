'''
Lambda function does the below
    Read alarms from json file (cw_alarms_priorities.json)
    Add alarms to dynamoDB table - FtCloudWatchAlarmsIncidentPriorities

The trigger of this lambda function is by a custom resource from cft aws_cw_alarms_priorities.yaml
'''

import os
import json
import boto3
import botocore
from botocore.config import Config
import http.client
from signal import alarm
import urllib.parse

alarms_ddb = os.environ['CWAlarmsDDB']
f = open('cw_alarms_priorities.json') 
def_alarms_priorities = json.load(f)

config = Config(retries=dict(max_attempts=10,mode='standard'))
ddb_resource = boto3.resource('dynamodb', config=config)

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
        except:
            print("Failed to send the response to the provided URL")
    return response

def handler(event, context):
    try:
        print('Event Received - ', event)

        response = {}
        response['Status'] = 'SUCCESS'
        response['Reason'] = 'See the details in CloudWatch Log Stream: ' + context.log_stream_name
        response['PhysicalResourceId'] = context.log_stream_name
        response['StackId'] = event['StackId']
        response['RequestId'] = event['RequestId']
        response['LogicalResourceId'] = event['LogicalResourceId']
        response['NoEcho'] = False

        if (event['RequestType'] in ['Create','Update']) and ('ServiceToken' in event):
            try:
                table = ddb_resource.Table(alarms_ddb)
                for alarm in def_alarms_priorities:
                    name = '-'.join([alarm['Service'], "".join(alarm['Metric'].split()), alarm['AlarmType'], alarm['Priority']])
                    item = {
                            'Service-Metric-Priority': name,
                            'Threshold': str(alarm['Threshold'])
                            }
                    try:
                        table.put_item(Item=item,
                                    ConditionExpression='attribute_not_exists(Service) AND attribute_not_exists(Threshold)')
                        print('Item - "{}" added to ddb - {}'.format(name, alarms_ddb))
                    except botocore.exceptions.ClientError as e:
                        if('ConditionalCheckFailedException' in str(e)):
                            print('Skip add {} Item already exist'.format(name))
                            continue                
                send_response(event, response, status='SUCCESS', reason='Lambda Completed')
            except Exception as e:
                print('Error', e)
                send_response(event, response, status='FAILED', reason=str(e))

        if (event['RequestType'] in ['Delete']) and ('ServiceToken' in event):
            send_response(event, response, status='SUCCESS', reason='Delete event received')

        return {
            'statusCode': 200,
        }
    except Exception as e:
        print('Lambda Execution Error ',e)
