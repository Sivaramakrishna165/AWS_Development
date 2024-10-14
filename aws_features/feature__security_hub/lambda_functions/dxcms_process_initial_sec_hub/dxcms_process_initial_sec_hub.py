# dxcms_process_initial_sec_hub.py

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
import ast
logger = logging.getLogger()
logger.setLevel(logging.INFO)
from boto3.dynamodb.conditions import Key, Attr
import datetime

config = Config(retries=dict(max_attempts=10,mode='standard'))
sec_hub_client = boto3.client('securityhub',config=config)
sns_client = boto3.client('sns',config=config)
log_client = boto3.client('logs',config=config)
dynamodb_resource = boto3.resource('dynamodb', config=config)
table = dynamodb_resource.Table('AccountFeatureDefinitions')
feature_name = 'SecurityHub'
val_to_fetch = 'pfSnowInciPriority'
currentDT = datetime.datetime.now()
Date_time= currentDT.strftime("%Y%m%d_%H%M%S")

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
        
            #p_enabled_standards_string = os.environ['ENABLED_STANDARDS_LIST']
            enabled_product_integrations_string = os.environ['ENABLED_PRODUCT_INTEGRATIONS_LIST']
            severity_string = os.environ['SEVERITY_LIST']
            sechub_region = os.environ['SECHUB_REGION']
            aws_account_id = os.environ['AWS_ACCOUNTID']
            topic_arn = os.environ['SNS_TOPIC']
        
            #if p_enabled_standards_string:
            #    p_enabled_standards_list = p_enabled_standards_string.split(',')
            #else:
            #    p_enabled_standards_list = []
            #print("p_enabled_standards_list entering the lambda is: ", p_enabled_standards_list)
        
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

            # DON'T send all disabled standards findings of the same severity level to ServiceNow as one Incident, ONLY mark SUPPRESSED, per PCLS
            target_wf_status = 'SUPPRESSED'
            all_severity_list = ['INFORMATIONAL', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'] 
            for sev in all_severity_list:
                get_all_standards_findings_by_severity_result = get_all_standards_findings_by_severity(sev,sechub_region)
                #formatMessage_disabled_standards_result = formatMessage_disabled_standards(get_all_standards_findings_by_severity_result['all_findings_obj'], sev, aws_account_id)
                if topic_arn: 
                    #send_standards_findings_to_ServiceNow_result = send_to_ServiceNow(formatMessage_disabled_standards_result['formatted_snow_message'], topic_arn)
                    for StdFinding in get_all_standards_findings_by_severity_result['all_findings_obj']:
                        print("StdFinding is: ", StdFinding)
                        set_workflow_status_result = set_workflow_status(StdFinding, target_wf_status)

            # Send each enabled integrations (products) finding of designated severity level to ServiceNow as one Incident and mark NOTIFIED
            target_wf_status = 'NOTIFIED'
            if severity_list and enabled_product_integrations_list and topic_arn:
                finding_id_prefix_list = xlat_int_prod_sub_arn_to_id_prefix(enabled_product_integrations_list) 
                get_sechub_findings_result = get_sechub_findings(severity_list, finding_id_prefix_list) 
                for IntegrationFinding in get_sechub_findings_result['all_findings_obj']:
                    formatMessage_result = formatMessage(event,IntegrationFinding) 
                    send_integrations_findings_to_FtCommonServiceNow_result = send_to_FtCommonServiceNow(formatMessage_result['formatted_snow_message'], topic_arn)
                    set_product_workflow_status_result = set_workflow_status(IntegrationFinding, target_wf_status)
            else:
                print("Invalid input, severity_list or enabled_product_integrations_list is empty")
                lambda_result = "Invalid input, severity_list or enabled_product_integrations_list is empty"
                exit

        except Exception as e:
            print('Error: Get findings for all disabled standards and send to FtCommonServiceNow()-', e)
            except_reason = "Exception error getting standards findings or sending to FtCommonServiceNow"
            lambda_result = except_reason
            
        except ClientError as e:
            ClientError_reason = e.response['Error']['Code']
            print("ClientError_reason is: ", ClientError_reason)
            except_reason = "ClientError in Get findings for all disabled standards and send to FtCommonServiceNow"
            lambda_result = except_reason
    
            except_reason = "ClientError in dxcms_disable_def_sec_hub_chk.py lambda loop"

    else:
        print("Not initial stack creation, skipping dxcms_disable_def_sec_hub_chk.py lambda function")

    # process DELETE event
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

def xlat_int_prod_sub_arn_to_id_prefix(enabled_product_integrations_list):
    id_prefix_list = []
    for sub_arn in enabled_product_integrations_list:
        int_prod_sub_arn = sub_arn
        int_prod_sub_arn_list = int_prod_sub_arn.split('product-subscription')
        suffix = int_prod_sub_arn_list[1]
        suffix_sub = suffix.replace('/',':')
        prefix = 'arn' + suffix_sub
        print("suffix_sub is: ", suffix_sub)
        #print("prefix is: ", prefix)
        id_prefix_list.append(prefix)
    return id_prefix_list
 
def set_workflow_status(finding, target_wf_status):
    # finding is a single finding, get the Id and ProductArn, then set desired status

    response = sec_hub_client.batch_update_findings(
        FindingIdentifiers=[
            {
                'Id': finding['Id'],
                'ProductArn': finding['ProductArn'] 
            }
        ],
        Note={
            'Text': 'Lambda automation',
            'UpdatedBy': 'Lambda automation'
        },
        Workflow={
            'Status': target_wf_status
        }
    )

def get_all_standards_findings_by_severity(sev,sechub_region):
    std_ProductArn = 'arn:aws:securityhub:' + sechub_region + '::product/aws/securityhub'
    SeverityLabelList = [{"Value":sev,"Comparison":"EQUALS"}]
    ProductArnList = [{"Value":std_ProductArn,"Comparison":"EQUALS"}]
    #new_Filter = '{"ProductArn":[{"Value": "arn:aws:securityhub:ap-northeast-1::product/aws/securityhub","Comparison":"EQUALS"}],"SeverityLabel": [{"Value":"HIGH","Comparison":"EQUALS"}]}'
    new_Filter = {"SeverityLabel": SeverityLabelList, "ProductArn": ProductArnList}

    print("std_ProductArn is: ", std_ProductArn)
    
    get_all_standards_findings_by_severity_response = {'all_findings_obj': None, 'reason': None}
    except_reason = None
    try:
        print("Retrieving findings by severity")
        NextToken = '' # Initialize in case MaxResults greater than 100 
        while(NextToken is not None):
            if NextToken is None or NextToken == '':
                get_findings_response = sec_hub_client.get_findings(
                    Filters=new_Filter
                )
            else:
                get_findings_response = sec_hub_client.get_findings(
                    Filters=new_Filter,
                    NextToken=NextToken,
                    MaxResults=100
                )
            NextToken = get_findings_response['NextToken'] if('NextToken' in get_findings_response) else None
        print("get_findings_response in get_all_standards_findings_by_severity is: ", get_findings_response)

    except Exception as e:
        print('Error:get_all_standards_findings_by_severity()-', e)
        except_reason = "Exception error in get_all_standards_findings_by_severity"
    except ClientError as e:
        ClientError_reason = e.response['Error']['Code']
        print("ClientError_reason is: ", ClientError_reason)
        except_reason = "ClientError in get_all_standards_findings_by_severity"

    if except_reason is not None:
        get_all_standards_findings_by_severity_response['reason'] = except_reason
        return get_all_standards_findings_by_severity_response 
    else:
        get_all_standards_findings_by_severity_response['all_findings_obj'] = get_findings_response['Findings'] 
        get_all_standards_findings_by_severity_response['reason'] = 'SUCCESS'
        print("success in get_all_standards_findings_by_severity_response, returning get_all_standards_findings_by_severity_response: ", get_all_standards_findings_by_severity_response) 
        return get_all_standards_findings_by_severity_response 

def get_sechub_findings(severity_list, finding_id_prefix_list):
    except_reason = None
    try:
        input_WorkflowStatus_list = ['NEW']
        search_severity_list = []
        search_WorkflowStatus_list = []
        search_finding_id_prefix_list = []
        
        one_sev_dict = {}
        for sev in severity_list:
            one_sev_dict = {"Value": sev, "Comparison": "EQUALS"}
            search_severity_list.append(one_sev_dict)
        
        one_workflow_status_dict = {}
        for onestat in input_WorkflowStatus_list:
            one_workflow_status_dict = {"Value": onestat, "Comparison": "EQUALS"}
            search_WorkflowStatus_list.append(one_workflow_status_dict)
        
        # use Id here because ProductArn not consistent (with/without AccountId)
        one_finding_id_prefix_dict = {}
        for IdPrefix in finding_id_prefix_list:
            one_finding_id_prefix_dict = {"Value": IdPrefix, "Comparison": "PREFIX"}
            search_finding_id_prefix_list.append(one_finding_id_prefix_dict)

        #print("search_severity_list is: ", search_severity_list)
        #print("search_WorkflowStatus_list: ", search_WorkflowStatus_list)
        
        new_Filter = {"SeverityLabel": search_severity_list, "WorkflowStatus": search_WorkflowStatus_list, "Id": search_finding_id_prefix_list}
        
        print("new_Filter in get_sechub_findings is: ", new_Filter)
        
        get_sechub_findings_response = {'all_findings_obj': None, 'reason': None}
        print("Retrieving findings")
        NextToken = '' # Initialize in case MaxResults greater than 123 
        while(NextToken is not None):
            if NextToken is None or NextToken == '':
                get_findings_response = sec_hub_client.get_findings(
                    Filters=new_Filter
                )
            else:
                get_findings_response = sec_hub_client.get_findings(
                    Filters=new_Filter,
                    NextToken=NextToken,
                    MaxResults=100
                )
            NextToken = get_findings_response['NextToken'] if('NextToken' in get_findings_response) else None
        print("get_findings_response in get_findings is: ", get_findings_response)

    except Exception as e:
        print('Error:get_sechub_findings()-', e)
        except_reason = "Exception error in get_sechub_findings"
    except ClientError as e:
        ClientError_reason = e.response['Error']['Code']
        print("ClientError_reason is: ", ClientError_reason)
        except_reason = "ClientError in get_sechub_findings"

    if except_reason is not None:
        get_sechub_findings_response['reason'] = except_reason
        return get_sechub_findings_response
    else:
        get_sechub_findings_response['all_findings_obj'] = get_findings_response['Findings'] 
        get_sechub_findings_response['reason'] = 'SUCCESS'
        print("success in get_sechub_findings, returning get_sechub_findings_response: ", get_sechub_findings_response) 
        return get_sechub_findings_response

## commented out and not sending to ServiceNow, per PCLS 
#def formatMessage_disabled_standards(finding_list, sev, aws_account_id):
#    # input is a list of findings for disabled standards, one severity level
#    #     This will be called once per severity level
#    # Build the json to send to ServiceNow
#    # eventMsg is the json data passed to ServiceNow for creating a ServiceNow event
#    except_reason = None
#    #target_wf_status = 'SUPPRESSED'
#    #dimensions_value = 'bySeverity'
#    formatMessage_disabled_standards_response = {'formatted_snow_message': None, 'reason': None} 
#    description = 'Security Hub severity ' + sev + ' disabled standards finding'
#    print("Building disabled standards json to send to ServiceNow")
#    try:
#        print("finding list passed in to formatMessage_disabled_standards is: ", finding_list)
#        eventMsg = {
#          "Trigger": {
#            "MetricName": description,
#            "Dimensions": [
#              {
#                "name": "InstanceId",
#                "value": description 
#              }
#            ]
#          },
#          "AlarmName": description,
#          "NewStateReason": description,
#          "AWSAccountId": aws_account_id,
#          "NewStateValue": "ALARM",
#          "correlation_id": description,
#          "InstanceId": description
#        }
#        eventMsg['eventData'] = finding_list
#        eventMsg['err'] = None
#
#        # Format the payload to send to SNS, https only for now, no e-mail
#        message = 'Sending a Security Hub disabled standards severity finding to ServiceNow via SNS' 
#        snsJson = {}
#        snsJson['default'] = message
#        snsJson['https'] = json.dumps(eventMsg)
#        snsJsonMsg = json.dumps(snsJson)
#        # question - whether or not an e-mail message has to be sent?  for now, no 
#
#        print("snsJsonMsg is: ", snsJsonMsg)
#        print("type of snsJsonMsg is: ", type(snsJsonMsg))
#
#    except Exception as e:
#        print('Error:formatMessage()-', e)
#        except_reason = 'Error in formatMessage' 
#
#    if except_reason is not None:
#        formatMessage_disabled_standards_response['reason'] = except_reason
#        return formatMessage_disabled_standards_response
#    else:
#        formatMessage_disabled_standards_response['formatted_snow_message'] = snsJsonMsg 
#        formatMessage_disabled_standards_response['reason'] = 'SUCCESS'
#        return formatMessage_disabled_standards_response

# This method will read the data from ADS Dynamo Db table to get the object
        
def get_db_object():
        try:
            response = table.query(KeyConditionExpression=Key('Feature').eq(feature_name))
            print('Response-', response)

            for item in response['Items']:
                fetched_object = item['FeatureParams'][val_to_fetch]['Default']
                print('fetched_object:',fetched_object)

            return fetched_object
        except Exception as e:
            print('error in get_db_object():',e)
            raise

def formatMessage(event,finding):
    # input is a single finding object
    # porting from pushMessage in backupHealth.js
    # Build the json to send to FtCommonServiceNow
    # eventMsg is the json data passed to FtCommonServiceNow for creating a ServiceNow event
    except_reason = None
    formatMessage_response = {'formatted_snow_message': None, 'reason': None} 
    print("Building json to send to FtCommonServiceNow")
    if finding['ProductFields']['aws/securityhub/ProductName']:
        prod_name = finding['ProductFields']['aws/securityhub/ProductName']
    else:
        prod_name = 'Third party product'

    try:
        print("finding passed in to formatMessage is: ", finding)
        eventMsg = {
            "EventList":[
            {
               "Trigger": {
                   "MetricName": finding['ProductArn'],
                   "Dimensions": [
                       {
                           "name": "InstanceId",
                           "value": finding['Id'] 
                       }
                    ]
                },
                "AlarmName": finding['Title'],
                "NewStateReason": finding['GeneratorId'],
                "AWSAccountId": finding['AwsAccountId'],
                "NewStateValue": "ALARM",
                "correlation_id": finding['Id'],
                "InstanceId": finding['Id'],        
                "eventsourcesendingserver": "feature__security_hub",
                "eventsourceexternalid": finding['Id'],
                "title" : 'test from Security Hub, might not be needed',
                "longDescription": finding['Description'],
                "application" : finding['ProductArn'],
                "eventsourcecreatedtime" : Date_time,
                "PriorityData" : {
                    "Priority" : get_db_object()
                }
            }
            ]
        }
        eventMsg['eventData'] = finding
        eventMsg['err'] = None

        # Format the payload to send to SNS, https only for now, no e-mail
        message = 'Security Hub finding for ' + prod_name + ' in ' + finding['AwsAccountId'] 
        snsJson = {}
        snsJson['default'] = message
        snsJson['https'] = json.dumps(eventMsg)
        snsJsonMsg = json.dumps(snsJson)
        Evntmsg = eventMsg
        # question - whether or not an e-mail message has to be sent?  for now, no 

        print("snsJsonMsg is: ", snsJsonMsg)
        print("type of snsJsonMsg is: ", type(snsJsonMsg))

    except Exception as e:
        print('Error:formatMessage()-', e)
        except_reason = 'Error in formatMessage' 

    if except_reason is not None:
        formatMessage_response['reason'] = except_reason
        return formatMessage_response
    else:
        formatMessage_response['formatted_snow_message'] = Evntmsg 
        formatMessage_response['reason'] = 'SUCCESS'
        return formatMessage_response


def send_to_FtCommonServiceNow(snow_message, topic_arn):
    except_reason = None
    try:
        print("sending Security Hub findings to FtCommonServiceNow via SNS")
        print("snow_message in send_to_FtCommonServiceNow is: ", snow_message)
        sns_client_response = sns_client.publish(
            MessageStructure='json',
            Message=json.dumps(
                        {'default': json.dumps(snow_message)}
                    ),
            Subject='test from Security Hub, might not be needed',
            TopicArn=topic_arn
        )
        print("sns_client_response is: ", sns_client_response)

    except Exception as e:
        print('Error:send_to_FtCommonServiceNow()-', e)
        except_reason = 'Error in send_to_FtCommonServiceNow' 

    if except_reason is not None:
        return except_reason
    else:
        return 'SUCCESS'


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
