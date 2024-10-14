'''
    If deployment of feature__m2_run_env is attempted in an unsupported region
    this lambda is called to send a failure signal back to the CFT
    to alert the user.
''' 
import boto3
import json, datetime
import urllib3
import os
import logging
from botocore.exceptions import ClientError
from botocore.config import Config

logger = logging.getLogger()
logger.setLevel(logging.INFO)


http = urllib3.PoolManager()
SUCCESS = "SUCCESS"
FAILED = "FAILED"


def send_response(event, context, responseStatus, responseData, physicalResourceId=None, noEcho=False, reason=None):
    try:
        responseUrl = event['ResponseURL']
        responseBody = {
            'Status' : responseStatus,
            'Reason' : "{}, See the details in CloudWatch Log Stream: {}".format(reason,context.log_stream_name),
            'PhysicalResourceId' : context.log_stream_name,
            'StackId' : event['StackId'],
            'RequestId' : event['RequestId'],
            'LogicalResourceId' : event['LogicalResourceId'],
            'NoEcho' : noEcho,
            'Data' : {'ReturnData':responseData}
        }
    
        json_responseBody = json.dumps(responseBody)
    
        print("Response body:")
        print(json_responseBody)
    
        headers = {
            'content-type' : '',
            'content-length' : str(len(json_responseBody))
        }
        try:
            response = http.request('PUT', responseUrl, headers=headers, body=json_responseBody)
            print("Status code:", response.status)

        except Exception as e:
            print("send(..) failed executing http.request(..):", e)
    except Exception as e:
        print('Error send_response() - ',e)
        raise


def lambda_handler(event, context):
    print('Event Received - ',event)
    print('Context Received - ',context)
    request_type = event['RequestType']

    lambda_result = None 

    ###  process Delete event
    if request_type in ['Delete'] and ('ServiceToken' in event):
        print("Processing Delete event in lambda_handler")
        return(send_response(event, context, 'SUCCESS', 'lambda_handler processing Delete event',None, None, 'lambda_handler processing Delete event'))


    ###  process Create event
    if request_type in ['Create'] and ('ServiceToken' in event):
        print("Unsupported M2 region, failing stack creation")
        return(send_response(event, context, 'FAILED', 'lambda_handler exiting unsupported M2 region',None, None, 'lambda_handler exiting unsupported M2 region'))

    ### End lambda, send final status to the stack
    print("end of lambda handler")
    print("send_response_dict['responseStatus'] is ", send_response_dict['responseStatus'])
    print("send_response_dict['responseData'] is ", send_response_dict['responseData'])
    send_response(event, context, send_response_dict['responseStatus'], send_response_dict['responseData'])
