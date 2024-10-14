"""
Lambda function that enables aws inspector v2
As of now there is no IaC tool which can be used to enable Inspector V2, so will be making use of boto3 api calls,

Sample Call:

{

}

"""
import json, os
import http.client
import urllib.parse

from enable_aws_inspector import (enable_aws_inspector)

afd_table = 'AccountFeatureDefinitions'
feature_name = 'AwsInspectorV2'

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
    
    print('received event:',event)

    try:

        response = {}
        if (event['RequestType'] in ['Create','Update','Delete']) and ('ServiceToken' in event):            
            response['Status'] = 'SUCCESS'
            response['Reason'] = 'See the details in CloudWatch Log Stream: ' + context.log_stream_name
            response['PhysicalResourceId'] = context.log_stream_name
            response['StackId'] = event['StackId']
            response['RequestId'] = event['RequestId']
            response['LogicalResourceId'] = event['LogicalResourceId']
            response['NoEcho'] = False

        if('RequestType' in event):
            if (event['RequestType'] in ['Create','Update']) and ('ServiceToken' in event):

                enable_inspector = enable_aws_inspector()
                resource_types = enable_inspector.get_resource_types(afd_table, feature_name)
                resource_list = resource_types.split(',')
                print('Resource List -',resource_list)                
                enable_inspector.handler_impl(event, context, resource_list)
                send_response(event, response, status='SUCCESS', reason='Inspector V2 enabled')

            # Update or Delete of Stack - Only send the response to CF after deleting the parameters
            else:
                print('Nothing to perform. {} event received'.format(event['RequestType']))
                send_response(event, response, status='SUCCESS', reason='{} event received'.format(event['RequestType']))

        print('process completed')

    except Exception as e:
        print('Error lambda_handler() ', e)
        if (event['RequestType'] in ['Create','Update','Delete'] and 'ServiceToken' in event):
            send_response(event, response, status='SUCCESS', reason='Lambda Failed')
