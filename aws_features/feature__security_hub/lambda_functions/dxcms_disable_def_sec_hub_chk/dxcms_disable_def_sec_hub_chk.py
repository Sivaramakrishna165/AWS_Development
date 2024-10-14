# dxcms_disable_def_sec_hub_chk.py

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
            ### Environment variables from CFT
            
            enabled_standards_string = os.environ['ENABLED_STANDARDS_LIST']
            enabled_product_integrations_string = os.environ['ENABLED_PRODUCT_INTEGRATIONS_LIST']
            severity_string = os.environ['SEVERITY_LIST']
            sechub_region = os.environ['SECHUB_REGION']
            aws_account_id = os.environ['AWS_ACCOUNTID']

            p_enabled_standards_string = enabled_standards_string.format(region = sechub_region, accountid = aws_account_id)
            
            if p_enabled_standards_string:
                p_enabled_standards_list = p_enabled_standards_string.split(',')
            else:
                p_enabled_standards_list = []
            print("p_enabled_standards_list entering the lambda is: ", p_enabled_standards_list)
            
            if enabled_product_integrations_string:
                enabled_product_integrations_list = enabled_product_integrations_string.split(',')
            else:
                enabled_product_integrations_list = []
            print("enabled_product_integrations_list entering the lambda is: ", enabled_product_integrations_list)
            
            if severity_string:
                severity_list = severity_string.split(',')
            else:
                severity_list = []
            print("severity_list entering the lambda is: ", severity_list)
            
            lambda_result = None    
            actual_enabled_standards_list = get_enabled_standards_list()
            if (actual_enabled_standards_list['reason'] == 'InvalidAccessException') and (event['RequestType'] == 'Delete'):
                lambda_result = None
            elif actual_enabled_standards_list['reason'] != 'SUCCESS':
                lambda_result = actual_enabled_standards_list['reason'] 
            
            # Disable all standards during stack creation because p_enabled_standards_list is blank.
            normalize_all_standards_result = normalize_all_standards(actual_enabled_standards_list['arn_list'], p_enabled_standards_list)
            if (normalize_all_standards_result == 'InvalidAccessException') and (event['RequestType'] == 'Delete'):
                lambda_result = None
            elif normalize_all_standards_result != 'SUCCESS':
                lambda_result = normalize_all_standards_result
            
            # Disable all integrations except GuardDuty (only GuardDuty in enabled_product_integrations_list).
            normalize_products_result = normalize_products(enabled_product_integrations_list)
            if normalize_products_result != 'SUCCESS':
                lambda_result = normalize_products_result 
            
            # Verify no standards are enabled, because p_enabled_standards_list is blank
            check_enabled_standards_result = check_enabled_standards(p_enabled_standards_list)
            if check_enabled_standards_result != 'SUCCESS':
                lambda_result = check_enabled_standards_result
            
            # Verify only the desired integration (GuardDuty)is enabled
            check_enabled_products_result = check_enabled_products(enabled_product_integrations_list)
            if check_enabled_products_result != 'SUCCESS':
                lambda_result = check_enabled_products_result

        except Exception as e:
            print('Error:dxcms_disable_def_sec_hub_chk.py lambda loop()-', e)
            except_reason = "Exception error in dxcms_disable_def_sec_hub_chk.py lambda loop"
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


def get_enabled_standards_list():
    get_enabled_standards_list_response = {'arn_list': None, 'reason': None}
    except_reason = None
    try:
        print("Fetching list of available standards")
        NextToken = '' # Initialize in case MaxResults greater than 123 
        while(NextToken is not None):
            if NextToken is None or NextToken == '':
                get_enabled_standards_response = sec_hub_client.get_enabled_standards() 
            else:
                get_enabled_standards_response = sec_hub_client.get_enabled_standards(
                    NextToken=NextToken,
                    MaxResults=123
                )
            NextToken = get_enabled_standards_response['NextToken'] if('NextToken' in get_enabled_standards_response) else None
        print("get_enabled_standards_response is ", get_enabled_standards_response)
    
        enabled_arn_list = []
        for standard in get_enabled_standards_response['StandardsSubscriptions']:
            enabled_arn_list.append(standard['StandardsSubscriptionArn'])
        
        print("enabled_arn_list is: ", enabled_arn_list)

    except Exception as e:
        print('Error:get_enabled_standards()-', e)
        except_reason = "Exception error in get_enabled_standards"
    except ClientError as e:
        ClientError_reason = e.response['Error']['Code']
        print("ClientError_reason is: ", ClientError_reason)
        except_reason = "ClientError in get_sechub_findings"

    if except_reason is not None:
        get_enabled_standards_list_response['reason'] = except_reason
        return get_enabled_standards_list_response 
    else:
        get_enabled_standards_list_response['arn_list'] = enabled_arn_list
        get_enabled_standards_list_response['reason'] = 'SUCCESS'
        return get_enabled_standards_list_response 

def normalize_all_standards(actual_enabled_standards_arn_list, p_enabled_standards_list):
    except_reason = None
    try:
        ### disable all desired standards (if p_enabled_standards_list is blank)
        print("actual_enabled_standards_arn_list in normalize all standards is: ", actual_enabled_standards_arn_list)
        print("p_enabled_standards_list in normalize all standards is: ", p_enabled_standards_list)
        delete_list = list(set(actual_enabled_standards_arn_list) - set(p_enabled_standards_list)) 
        print("delete_list in normalize all standards is: ", delete_list)
        if delete_list:
            print("Disabling non-desired standards")
            batch_disable_standards_response = sec_hub_client.batch_disable_standards(
                StandardsSubscriptionArns=delete_list
            )
            print("batch_disable_standards_response is: ", batch_disable_standards_response)
        else:
            print("No standards to delete")


    except Exception as e:
        print('Error:normalize_all_standards()-', e)
        except_reason = 'Error in normalize_all_standards' 

    except ClientError as e:
        ClientError_reason = e.response['Error']['Code']
        print("ClientError_reason in normalize_all_standards is: ", ClientError_reason)
        except_reason = "ClientError in normalize_all_standards"

    if except_reason is not None:
        return except_reason
    else:
        return 'SUCCESS'


def normalize_products(enabled_product_integrations_list):
    desired_product_sub_arn_list = sorted(enabled_product_integrations_list)
    except_reason = None
    try:
        ### Get list of enabled products
        print("Fetching list of enabled products")
        NextToken = '' # Initialize in case MaxResults greater than 123
        while(NextToken is not None):
            if NextToken is None or NextToken == '':
                list_enabled_products_for_import_response = sec_hub_client.list_enabled_products_for_import()
            else:
                list_enabled_products_for_import_response = sec_hub_client.list_enabled_products_for_import(
                    NextToken=NextToken,
                    MaxResults=123
                )
            NextToken = list_enabled_products_for_import_response['NextToken'] if('NextToken' in list_enabled_products_for_import_response) else None
        print("list_enabled_products_for_import_response is ", list_enabled_products_for_import_response)
        actual_prod_sub_arn_list = sorted(list_enabled_products_for_import_response['ProductSubscriptions'])

        ### disable non desired products
        delete_list = list(set(actual_prod_sub_arn_list) - set(desired_product_sub_arn_list)) 
        print("delete_list in normalize_products is: ", delete_list)
        if delete_list:
            print("Disabling non-desired products")
            for product in delete_list:
                disable_import_findings_for_product_response = sec_hub_client.disable_import_findings_for_product(
                    ProductSubscriptionArn=product
                )
            print("completed disabling products ")
        else:
            print("Current products = desired products")


    except Exception as e:
        print('Error:normalize_products()-', e)
        except_reason = 'Error in normalize_products'

    except ClientError as e:
        ClientError_reason = e.response['Error']['Code']
        print("ClientError_reason in normalize_products is: ", ClientError_reason)
        except_reason = "ClientError in normalize_products"

    if except_reason is not None:
        return except_reason
    else:
        return 'SUCCESS'


def check_enabled_standards(p_enabled_standards_list):
    except_reason = None
    try:
        print("checking for enabled standards")
        check_status = None
        while check_status is None:
            NextToken = '' # Initialize in case MaxResults greater than 123 
            while(NextToken is not None):
                if NextToken is None or NextToken == '':
                    check_enabled_standards_response = sec_hub_client.get_enabled_standards() 
                else:
                    check_enabled_standards_response = sec_hub_client.get_enabled_standards(
                        NextToken=NextToken,
                        MaxResults=123
                    )
                NextToken = check_enabled_standards_response['NextToken'] if('NextToken' in check_enabled_standards_response) else None
            statuslist = []
            for subscript in check_enabled_standards_response['StandardsSubscriptions']:
                statuslist.append(subscript['StandardsStatus']) 
            print("statuslist is: ", statuslist)            
            set1 = set(statuslist)
            if 'DELETING' in set1:
                sleep(3)
            else:
                check_status = 'Done'
        print("check_enabled_standards_response['StandardsSubscriptions'] in check_enabled_standards is: ", check_enabled_standards_response['StandardsSubscriptions'])
        print("p_enabled_standards_list in check_enabled_standards is: ", p_enabled_standards_list)
        enabled_list = []
        for item in check_enabled_standards_response['StandardsSubscriptions']:
            enabled_list.append(item['StandardsSubscriptionArn'])
        enabled_list_sorted = sorted(enabled_list)
        p_list_sorted = sorted(p_enabled_standards_list)

    except Exception as e:
        print('Error:check_enabled_standards()-', e)
        except_reason = 'Error in check_enabled_standards' 

    if except_reason is not None:
        return except_reason
    else:
        if enabled_list_sorted == p_list_sorted:
            print("success - enabled standards = desired standards")
            check_enabled_standards_response_status = 'SUCCESS'
        else:
            print("failure, enabled standards do not match desired standards ")
            check_enabled_standards_response_status = 'FAILURE - enabled standards do not match desired standards'
        return check_enabled_standards_response_status 


def check_enabled_products(enabled_product_integrations_list):

    except_reason = None
    try:
        print("Fetching list of enabled products for checking")
        NextToken = '' # Initialize in case MaxResults greater than 123
        while(NextToken is not None):
            if NextToken is None or NextToken == '':
                check_enabled_products_response = sec_hub_client.list_enabled_products_for_import()
            else:
                check_enabled_products_response = sec_hub_client.list_enabled_products_for_import(
                    NextToken=NextToken,
                    MaxResults=123
                )
            NextToken = check_enabled_products_response['NextToken'] if('NextToken' in check_enabled_products_response) else None
        print("check_enabled_products_response is ", check_enabled_products_response)
    except Exception as e:
        print('Error:check_enabled_products()-', e)
        except_reason = 'Error in check_enabled_products' 

    # Security Hub itself counts as a subscription
    enabled_list = []
    for product in check_enabled_products_response['ProductSubscriptions']:
        enabled_list.append(product)
    enabled_list_sorted = sorted(enabled_list)
    desired_list_sorted = sorted(enabled_product_integrations_list)

    if except_reason is not None:
        return except_reason
    else:
        if enabled_list_sorted == desired_list_sorted:
            print("success - Only desired products are enabled")
            check_enabled_products_response_status = 'SUCCESS'
        else:
            print("failure - enabled products list does not match desired products list")
            check_enabled_products_response_status = 'failure - enabled products list does not match desired products list'

        return check_enabled_products_response_status

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
