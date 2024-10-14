'''
- lambda which deletes the SSM Document : SSM-SessionManagerRunShell

Sample Request event:
        {'RequestType': 'Create', 
        'ServiceToken': 'arn:aws:lambda:eu-west-2:225992052696:function:dxc-awsms-SSMRunShellDocDelLambda-eu-west-2', 
        'ResponseURL': 'https://cloudformation-custom-resource-response-euwest2.s3.eu-west-2.amazonaws.com/arn%3Aaws%3Acloudformation%3Aeu-west-2%3A225992052696%3Astack/FeatureEC2SessionMonitoringStack-EC2SessionMonitoring-6MMDQ2WHA9WG/d39c6b70-fcfa-11ec-93c5-0642d56e6d5e%7CrSSMRunShellDocDelLambdaCustom%7C388d404a-5c7d-4b00-aa1d-3cc3413cb47e?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Date=20220706T071156Z&X-Amz-SignedHeaders=host&X-Amz-Expires=7200&X-Amz-Credential=AKIAZYWU4JB3THCK6ZGP%2F20220706%2Feu-west-2%2Fs3%2Faws4_request&X-Amz-Signature=dca3fc7a9c103711560efc331507339cdbe098a6eb45ea2bf049c9f826e24793',
        'StackId': 'arn:aws:cloudformation:eu-west-2:225992052696:stack/FeatureEC2SessionMonitoringStack-EC2SessionMonitoring-6MMDQ2WHA9WG/d39c6b70-fcfa-11ec-93c5-0642d56e6d5e', 
        'RequestId': '388d404a-5c7d-4b00-aa1d-3cc3413cb47e', 
        'LogicalResourceId': 'rSSMRunShellDocDelLambdaCustom', 
        'ResourceType': 'AWS::CloudFormation::CustomResource', 
        'ResourceProperties': {'ServiceToken': 'arn:aws:lambda:eu-west-2:225992052696:function:dxc-awsms-SSMRunShellDocDelLambda-eu-west-2'}
        }
'''

import json, os
from boto_helper import boto_helper
import http.client
import urllib.parse

boto_obj = boto_helper()

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
        except Exception as e:
            print("Failed to send the response to the provided URL",e)
    return response

def lambda_handler(event, context):

    try:

        print('Received Event:', event)

        doc_name = os.environ['doc_name']

        response = {}
        if (event['RequestType'] in ['Create','Update','Delete']) and ('ServiceToken' in event):            
            response['Status'] = 'SUCCESS'
            response['Reason'] = 'See the details in CloudWatch Log Stream: ' + context.log_stream_name
            response['PhysicalResourceId'] = context.log_stream_name
            response['StackId'] = event['StackId']
            response['RequestId'] = event['RequestId']
            response['LogicalResourceId'] = event['LogicalResourceId']
            response['NoEcho'] = False
            #response['Data'] = {}

        if('RequestType' in event):
            if (event['RequestType'] in ['Create','Update']) and ('ServiceToken' in event):

                #check if 'SSM-SessionManagerRunShell' present or not
                if boto_obj.check_document(doc_name):
                    print('doc present. delete it')
                    boto_obj.delete_document(doc_name)

                    send_response(event, response, status='SUCCESS', reason='Document Deleted')
                else:
                    print('doc not present.')
                    send_response(event, response, status='SUCCESS', reason='Document Not Present')

            # Delete of Stack - Only send the response to CF after deleting the parameters
            if (event['RequestType'] in ['Delete']) and ('ServiceToken' in event):
                send_response(event, response, status='SUCCESS', reason='Delete event received')


        print('process completed')

        return {
            'statusCode': 200,
            'body': "Lambda processed Successfully"
        }

    except Exception as e:
        print('Error lambda_handler() ', e)
        if (event['RequestType'] in ['Create','Update','Delete'] and 'ServiceToken' in event):
            send_response(event, response, status='SUCCESS', reason='Lambda Failed')