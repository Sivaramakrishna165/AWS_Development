'''
Lambda function does the below
    Generate HandShake/Invitation for Child account to map with Master Payer
    Add the handshake details in dynamoDB
    Send handhake details to SNS Topic

The trigger of this lambda function is by a custom resource from cft dxcms-add-aws-acc-to-master-payer.yaml
'''

import os
import json
import http.client
import urllib.parse
from boto_helper import boto_helper

boto_helper_obj = boto_helper()
acc_to_mp_topic = os.environ['AddAcctoMpTopic']
ft_name = os.environ['FtName']
ads_table = os.environ['ADSTable']
account = os.environ['EXECUTION_ACCOUNT']

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
                
                handshake_id = event['ResourceProperties']['HandshakeId']
                mode = event['ResourceProperties']['Mode']
                if ('ACCEPT' in mode):
                    handshake_resp = boto_helper_obj.accept_handshake(handshake_id)
                else:
                    handshake_resp = boto_helper_obj.decline_handshake(handshake_id)
                
                if(handshake_resp != None):
                    print('Handshake response - ', handshake_resp)
                    output = {}
                    output['HandshakeId'] = handshake_id
                    if('Handshake' in response):
                        output['Status'] = handshake_resp['Handshake']['State']
                    else:
                        output['Status'] = handshake_resp
                    boto_helper_obj.sns_publish(acc_to_mp_topic, output, 'AWSMS - AWS Orgs Account Map status - {}'.format(account))
                    
                    print('Process Completed') 
                send_response(event, response, status='SUCCESS', reason='Lambda Completed')
            except Exception as e:
                print('Error', e)
                response['Error'] = str(e)
                send_response(event, response, status='FAILED', reason=str(e))

        if (event['RequestType'] in ['Delete']) and ('ServiceToken' in event):
            send_response(event, response, status='SUCCESS', reason='Delete event received')

        return {
            'statusCode': 200,
        }
    except Exception as e:
        print('Lambda Execution Error ',e)