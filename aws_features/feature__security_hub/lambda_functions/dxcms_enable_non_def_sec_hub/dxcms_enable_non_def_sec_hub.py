'''
Lambda - dxcms_enable_non_def_sec_hub.py
This lambda function is created as part of AWSPE-6984
This lambda will trigger only once during the create event and enable the standards mentioned in the parameter pEnableNonDefaultStandardsList.
'''

import uuid
import json
import boto3
import logging
import string
import os
from botocore.exceptions import ClientError
import http.client
import urllib.parse
from time import sleep
from botocore.config import Config

logger = logging.getLogger()
logger.setLevel(logging.INFO)

config = Config(retries=dict(max_attempts=10,mode='standard'))
sec_hub_client = boto3.client('securityhub',config=config)

#To send the response back to cfn template
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

def enable_standards(p_enable_non_default_standards_list):
    except_reason = None
    try:            
        for std_arn in p_enable_non_default_standards_list:                    
            batch_enable_standards_response = sec_hub_client.batch_enable_standards(
                StandardsSubscriptionRequests=[
                    {
                        'StandardsArn': std_arn
                    },
                ]
            )
            print('Enabled -', std_arn)
    except Exception as e:
        print('Error enable_standards() lambda -', str(e))
        except_reason = 'Exception Error in enable_standards()'
        
    except ClientError as e:
        ClientError_reason = e.response['Error']['Code']
        print("ClientError_reason in enable_standards is: ", ClientError_reason)
        except_reason = "ClientError in enable_standards"
        
    if except_reason is not None:
        return except_reason
    else:
        return 'SUCCESS'               

def lambda_handler(event, context):
    
    print('Event Received-', event)

    response = {
        'StackId': event['StackId'],
        'RequestId': event['RequestId'],
        'LogicalResourceId': event['LogicalResourceId'],
        'Status': 'SUCCESS'
    }
    
    if event['RequestType'] == 'Create':
        
        try:
            enable_non_default_standards = os.environ['ENABLED_NON_DEFAULT_STANDARDS_LIST']
            sechub_region = os.environ['SECHUB_REGION']
            aws_account_id = os.environ['AWS_ACCOUNTID']            
            
            p_enable_non_default_standards_string = enable_non_default_standards.format(region = sechub_region, accountid = aws_account_id)
            
            if p_enable_non_default_standards_string:
                p_enable_non_default_standards_list = p_enable_non_default_standards_string.split(',')
                print("p_enable_non_default_standards_list entering the lambda is: ", p_enable_non_default_standards_list)
            else:
                p_enable_non_default_standards_list = ""
                print("p_enable_non_default_standards_list entering the lambda is: ", p_enable_non_default_standards_list)
                print("No standards to enable")
                if 'PhysicalResourceId' in event:
                    response['PhysicalResourceId'] = event['PhysicalResourceId']
                else:
                    response['PhysicalResourceId'] = str(uuid.uuid4())                   
                return send_response(
                    event,
                    response,
                    status='SUCCESS',
                    reason='No standards to enable.'
                )
                
            lambda_result = None
            #Enable the standards that are in the p_enable_non_default_standards_list
            enable_non_default_standards_list = enable_standards(p_enable_non_default_standards_list)
            if enable_non_default_standards_list != 'SUCCESS':
                lambda_result = enable_non_default_standards_list['reason']
            else:
                print('All the required standards are enabled')                 
            
        except Exception as e:
            print('Error:dxcms_enable_non_def_sec_hub.py lambda-', e)
            except_reason = "Exception error in dxcms_enable_non_def_sec_hub.py lambda"
            lambda_result = except_reason
        except ClientError as e:
            ClientError_reason = e.response['Error']['Code']
            print("ClientError_reason is: ", ClientError_reason)
            lambda_result = ClientError_reason
    else:
        print("Not initial stack creation, skipping dxcms_disable_def_sec_hub_chk.py lambda function")
        
    if 'PhysicalResourceId' in event:
        response['PhysicalResourceId'] = event['PhysicalResourceId']
    else:
        response['PhysicalResourceId'] = str(uuid.uuid4())                
        
    if event['RequestType'] == 'Delete':
        return send_response(
            event,
            response,
            status='SUCCESS',
            reason='Delete event received, nothing to do.'
        )        
        
    ## End the Lambda Function
    if lambda_result is not None:
        lambda_status = 'FAILED'
        lambda_reason = lambda_result
    else:
        lambda_status = 'SUCCESS'
        lambda_reason = 'Lambda completed successfully'
    
    return send_response(
        event,
        response,
        status=lambda_status,
        reason=lambda_reason
    )        