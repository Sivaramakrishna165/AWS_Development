import boto3
from dateutil.tz import tzutc
import json 
import os
import http.client
import urllib.parse
from botocore.exceptions import ClientError

from botocore.config import Config

from helper import sechub_historicaldata_export
sechub_hd_helper_obj = sechub_historicaldata_export()

"""
Feature that can generate Security Hub export to s3 when this feature is deployed
It will pull all the Historical Data from SH and dump it in s3

By : Sathyajith Puttaiah
"""

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
		print ('event:',event)
		finding_filter = sechub_hd_helper_obj.create_filter()
		response = {}
		if (event['RequestType'] in ['Create','Update','Delete']) and ('ServiceToken' in event):
			response['Status'] = 'SUCCESS'
			response['Reason'] = 'See the details in CloudWatch Log Stream: ' + context.log_stream_name
			response['PhysicalResourceId'] = context.log_stream_name
			response['StackId'] = event['StackId']
			response['RequestId'] = event['RequestId']
			response['LogicalResourceId'] = event['LogicalResourceId']
			response['NoEcho'] = False

		if ('RequestType' in event):
		    if (event['RequestType'] in ['Delete','Update']) and ('ServiceToken' in event):
		        send_response(event, response, status='SUCCESS', reason='Delete event received')
		    if ( event['RequestType'] in ['Create'] ) and ('ServiceToken' in event):
			    results = sechub_hd_helper_obj.get_findings(finding_filter)
			    sechub_hd_helper_obj.put_obj_to_s3(results)
			    sechub_count = sechub_hd_helper_obj.sechub_count_value(results)
			    
			    send_response(event, response, status='SUCCESS', reason='Report Completed')

	except Exception as e:
		print('Error lambda_handler() ', e)
		if (event['RequestType'] in ['Create','Update','Delete'] and 'ServiceToken' in event):
			send_response(event, response, status='SUCCESS', reason='Lambda Failed')