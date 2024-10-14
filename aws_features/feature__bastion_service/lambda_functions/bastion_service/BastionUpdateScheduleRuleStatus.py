import http.client
import urllib.parse
import json
import boto3
from botocore.config import Config
config = Config(retries=dict(max_attempts=10,mode='standard'))
aeb_client = boto3.client('events', config=config)
cf_client = boto3.client('cloudformation', config=config)
def send_response(request, response, status=None, reason=None):
    if status is not None:
        response['Status'] = status
    if reason is not None:
        response['Reason'] = reason
    if 'ResponseURL' in request and request['ResponseURL']:
        try:
            url = urllib.parse.urlparse(request['ResponseURL'])
            body = json.dumps(response)
            print('Body - ', body)
            https = http.client.HTTPSConnection(url.hostname)
            https.request('PUT', url.path + '?' + url.query, body)
            print('HTTP response sent successfully')
        except:
            print("Failed to send the response to the provided URL")
    return response
    
def BastionUpdateScheduleRuleStatus_handler(event, context):
    try:
        print('Event Received -',event)
        response = {}
        if (event['RequestType'] in ['Create','Update','Delete']) and ('ServiceToken' in event):            
            response['Status'] = 'SUCCESS'
            response['Reason'] = 'See the details in CloudWatch Log Stream: ' + context.log_stream_name
            response['PhysicalResourceId'] = context.log_stream_name
            response['StackId'] = event['StackId']
            response['RequestId'] = event['RequestId']
            response['LogicalResourceId'] = event['LogicalResourceId']
        
        rule_response = aeb_client.list_rules(NamePrefix='FeatureBastionServiceStack')
        for rule in rule_response['Rules']:
            if "FeatureBastionServiceStack-Service" in rule['Name']:
                rule_name = rule['Name']
            else:
                print("rule you are looking is not found")    
        rule_resp = aeb_client.describe_rule(Name=rule_name)
        args = {}
        flag = 0
        while True:
            stack_resp = cf_client.describe_stacks(**args)
            for stack in stack_resp['Stacks']:
                if 'Description' in stack:
                    if "bastion host valid for 60 minutes" in stack['Description'] and stack['StackStatus'] in ['CREATE_COMPLETE','UPDATE_COMPLETE','CREATE_IN_PROGRESS','UPDATE_IN_PROGRESS']:
                        flag = flag+1
            if 'NextToken' in stack_resp:
                args['NextToken']=stack_resp['NextToken']
            else:
                break
        if('RequestType' in event):
            if (event['RequestType'] in ['Create','Update']) and ('ServiceToken' in event):
                if rule_resp['State'] == "DISABLED":
                    enable_resp = aeb_client.enable_rule(Name=rule_name)
                else:
                    print("rule is already in Enabled state")
                send_response(event, response, status='SUCCESS', reason='Lambda Invoked')
            if (event['RequestType'] in ['Delete']) and ('ServiceToken' in event):
                if rule_resp['State'] == "ENABLED" and flag == 0:
                    disable_resp = aeb_client.disable_rule(Name=rule_name)
                else:
                    print("rule is already in Disabled state")
                send_response(event, response, status='SUCCESS', reason='Lambda Invoked')
        
        return {
            'statusCode': 200,
            'body': json.dumps('Hello from Lambda!')
        }
    except Exception as e:
        print('Error send_task_success()-',e)
        if (event['RequestType'] in ['Create','Update','Delete'] and 'ServiceToken' in event):
            send_response(event, response, status='SUCCESS', reason='Delete event received')
