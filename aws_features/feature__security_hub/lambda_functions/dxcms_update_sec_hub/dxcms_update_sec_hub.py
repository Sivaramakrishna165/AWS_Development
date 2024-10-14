# dxcms_update_sec_hub.py

import uuid
import json
import boto3
import logging
import string
import os
import base64
from botocore.exceptions import ClientError
import hashlib
import http.client
import urllib.parse
from time import sleep
from botocore.config import Config
logger = logging.getLogger()
logger.setLevel(logging.INFO)

config = Config(retries=dict(max_attempts=10,mode='standard'))
sec_hub_client = boto3.client('securityhub',config=config)

def lambda_handler(event, context):
    print('Event Received-', event)
    response = {
        'StackId': event['StackId'],
        'RequestId': event['RequestId'],
        'LogicalResourceId': event['LogicalResourceId'],
        'Status': 'SUCCESS'
    }

    ### Environment variables from CFT

    p_Update_StandardsSubscriptionArn_String = os.environ['UPDATE_STANDARDS_SUBSCRIPTION_ARN_LIST']
    p_Update_ProductsSubscriptionArn_String = os.environ['UPDATE_PRODUCTS_SUBSCRIPTION_ARN_LIST']
    p_Update_StandardsArn_String = os.environ['UPDATE_STANDARDS_ARN_LIST']
    p_Update_ProductArn_String = os.environ['UPDATE_PRODUCT_ARN_LIST']
    sechub_region = os.environ['SECHUB_REGION']
    aws_account_id = os.environ['AWS_ACCOUNTID']

    Update_StandardsSubscriptionArn_String=p_Update_StandardsSubscriptionArn_String.format(region = sechub_region, accountid = aws_account_id)
    Update_ProductsSubscriptionArn_String=p_Update_ProductsSubscriptionArn_String.format(region = sechub_region, accountid = aws_account_id)
    Update_StandardsArn_String=p_Update_StandardsArn_String.format(region = sechub_region, accountid = aws_account_id)
    Update_ProductArn_String=p_Update_ProductArn_String.format(region = sechub_region, accountid = aws_account_id)

    print("Update_StandardsSubscriptionArn_String is: ", Update_StandardsSubscriptionArn_String)
    print("Update_ProductsSubscriptionArn_String is: ", Update_ProductsSubscriptionArn_String)
    print("Update_StandardsArn_String is: ", Update_StandardsArn_String)
    print("Update_ProductArn_String is: ", Update_ProductArn_String)

    if Update_StandardsSubscriptionArn_String:
        Update_StandardsSubscriptionArn_List = Update_StandardsSubscriptionArn_String.split(',')
    else:
        Update_StandardsSubscriptionArn_List = []
    print("Update_StandardsSubscriptionArn_List in dxcms_update_sec_hub is: ", Update_StandardsSubscriptionArn_List)

    if Update_ProductsSubscriptionArn_String:
        Update_ProductsSubscriptionArn_List = Update_ProductsSubscriptionArn_String.split(',')
    else:
        Update_ProductsSubscriptionArn_List = []
    print("Update_ProductsSubscriptionArn_List in dxcms_update_sec_hub is: ", Update_ProductsSubscriptionArn_List)

    if Update_StandardsArn_String:
        Update_StandardsArn_List = Update_StandardsArn_String.split(',')
    else:
        Update_StandardsArn_List = []
    print("Update_StandardsArn_List in dxcms_update_sec_hub is: ", Update_StandardsArn_List)

    if Update_ProductArn_String:
        Update_ProductArn_List = Update_ProductArn_String.split(',')
    else:
        Update_ProductArn_List = []
    print("Update_ProductArn_List in dxcms_update_sec_hub is: ", Update_ProductArn_List)

    lambda_result = None    

    ### Disable standards
    try:

        if Update_StandardsSubscriptionArn_List:
            batch_disable_standards_response = sec_hub_client.batch_disable_standards(
                StandardsSubscriptionArns=Update_StandardsSubscriptionArn_List
            ) 
        else:
            print("No Standards to disable")

    except Exception as e:
        print('Error: with disable standards in dxcms_update_sec_hub()-', e)
        except_reason = "Exception error with disable standards in dxcms_update_sec_hub"
        lambda_result = except_reason
        
    except ClientError as e:
        ClientError_reason = e.response['Error']['Code']
        print("ClientError_reason is: ", ClientError_reason)
        except_reason = "ClientError with disable standards in dxcms_update_sec_hub"
        lambda_result = except_reason


    ### Disable integrations
    try:

        if Update_ProductsSubscriptionArn_List:
            for integration in Update_ProductsSubscriptionArn_List:
                disable_import_findings_for_product_response = sec_hub_client.disable_import_findings_for_product(
                    ProductSubscriptionArn=integration
                )
        else:
            print("No Integrations to disable") 

    except Exception as e:
        print('Error: with disable integrations in dxcms_update_sec_hub()-', e)
        except_reason = "Exception error with disable integrations in dxcms_update_sec_hub"
        lambda_result = except_reason
        
    except ClientError as e:
        ClientError_reason = e.response['Error']['Code']
        print("ClientError_reason is: ", ClientError_reason)
        except_reason = "ClientError with disable integrations in dxcms_update_sec_hub"
        lambda_result = except_reason


    ### Enable standards
    try:

        if Update_StandardsArn_List:
            formatted_std_arn_list = create_StandardsSubscriptionRequests_dict_list(Update_StandardsArn_List)
            batch_enable_standards_response = sec_hub_client.batch_enable_standards(
                StandardsSubscriptionRequests=formatted_std_arn_list
            )
        else:
            print("No standards to enable")

    except Exception as e:
        print('Error: with enable standards in dxcms_update_sec_hub()-', e)
        except_reason = "Exception error with enable standards in dxcms_update_sec_hub"
        lambda_result = except_reason
        
    except ClientError as e:
        ClientError_reason = e.response['Error']['Code']
        print("ClientError_reason is: ", ClientError_reason)
        except_reason = "ClientError with enable standards in dxcms_update_sec_hub"
        lambda_result = except_reason


    ### Enable integrations
    try:

        if Update_ProductArn_List:
            for OneProduct in Update_ProductArn_List:
                enable_import_findings_for_product_response = sec_hub_client.enable_import_findings_for_product(
                    ProductArn=OneProduct
                ) 
        else:
            print("No integrations to enable")

    except Exception as e:
        print('Error: with enable integrations in dxcms_update_sec_hub()-', e)
        except_reason = "Exception error with enable integrations in dxcms_update_sec_hub"
        lambda_result = except_reason
        
    except ClientError as e:
        ClientError_reason = e.response['Error']['Code']
        print("ClientError_reason is: ", ClientError_reason)
        except_reason = "ClientError with enable integrations in dxcms_update_sec_hub"
        lambda_result = except_reason


    ### process DELETE event
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

    ### End the Lambda Function
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


def create_StandardsSubscriptionRequests_dict_list(new_StandardArn_list):
    output_StdArn_list = []

    #search_severity_list = []
    #search_WorkflowStatus_list = []

    one_arn_dict = {}
    for arn in new_StandardArn_list:
        one_arn_dict = {"StandardsArn": arn}
        output_StdArn_list.append(one_arn_dict)
    print("StandardsSubscriptionRequests_dict_list is: ", output_StdArn_list)
    return output_StdArn_list


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
