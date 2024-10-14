# dxcms_sec_hub_to_service_now.py

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
from boto3.dynamodb.conditions import Key, Attr

config = Config(retries=dict(max_attempts=10,mode='standard'))
sec_hub_client = boto3.client('securityhub',config=config)
sns_client = boto3.client('sns',config=config)
log_client = boto3.client('logs',config=config)
dynamodb_resource = boto3.resource('dynamodb', config=config)
table = dynamodb_resource.Table('AccountFeatureDefinitions')
feature_name = 'SecurityHub'
val_to_fetch = 'pfSnowInciPriority'

def lambda_handler(event, context):

    ### Environment variables from CFT
    print('Event Received-', event)
    p_CompleteStandardsArn_string = os.environ['ENABLED_STANDARDS_LIST']
    p_CompleteProductArn_string = os.environ['ENABLED_PRODUCT_INTEGRATIONS_LIST']
    CompleteSeverity_string = os.environ['SEVERITY_LIST']
    sechub_region = os.environ['SECHUB_REGION']
    aws_account_id = os.environ['AWS_ACCOUNTID']
    topic_arn = os.environ['SNS_TOPIC']
    sh_to_snow_loggroup_retention = int(os.environ['SECHUB_SNOW_LOG_RETENTION'])

    CompleteStandardsArn_string=p_CompleteStandardsArn_string.format(region = sechub_region, accountid = aws_account_id)
    CompleteProductArn_string=p_CompleteProductArn_string.format(region = sechub_region, accountid = aws_account_id)

    if CompleteStandardsArn_string:
        CompleteStandardsArn_list = CompleteStandardsArn_string.split(',')
    else:
        CompleteStandardsArn_list = []
    print("CompleteStandardsArn_list entering the lambda is: ", CompleteStandardsArn_list)

    if CompleteProductArn_string:
        CompleteProductArn_list = CompleteProductArn_string.split(',')
    else:
        CompleteProductArn_list = []
    print("CompleteProductArn_list entering the lambda is: ", CompleteProductArn_list)

    if CompleteSeverity_string:
        CompleteSeverity_list = CompleteSeverity_string.split(',')
    else:
        CompleteSeverity_list = []
    print("CompleteSeverity_list entering the lambda is: ", CompleteSeverity_list)

    lambda_log_group_name = context.log_group_name
    put_retention_policy_response = describe_policy_response(lambda_log_group_name,sh_to_snow_loggroup_retention,tries=1)
    ### process EventBridge event from Security Hub, 
    ###   Derive a search string for each standard in CompleteStandardsArn_list to use for a get_findings Id search for the enabled standards.
    ###   Derive a search string for each integration in CompleteProductArn_list to use for a get_findings Id search for the enabled integrations
    ###   Process each finding in the event and if a desired standard or integration with the proper severity level exists, send to FtCommonServiceNow
    ###   For a standard or integration finding to be sent to FtCommonServiceNow, 
    ###     it must be listed in, and be of a severity listed in, the "Complete" parameter section of the CFT

    lambda_result = None    
    try:
        target_wf_status = 'NOTIFIED'
        if (CompleteSeverity_list and (CompleteStandardsArn_list or CompleteProductArn_list)):
            standards_substring_search_list = xlat_StandardsArn_to_search_substring(CompleteStandardsArn_list) 
            get_findings_from_event_result = get_findings_from_event(CompleteSeverity_list, standards_substring_search_list['substring_list'], CompleteProductArn_list, event) 
            if get_findings_from_event_result['all_findings_obj'] and topic_arn:
                for OneEventFinding in get_findings_from_event_result['all_findings_obj']:
                    formatMessage_result = formatMessage(event,OneEventFinding) 
                    send_integrations_findings_to_FtCommonServiceNow_result = send_to_FtCommonServiceNow(formatMessage_result['formatted_snow_message'], topic_arn, formatMessage_result['email_subject'])
                    set_product_workflow_status_result = set_workflow_status(OneEventFinding, target_wf_status)
            else:
                print("no findings meeting criteria, not sending to FtCommonServiceNow")
        else:    
            print("Empty severity list or no standards or integrations specified, nothing to send to FtCommonServiceNow")
            except_reason = "Error - no severity or no standard and no product"
            raise Exception('Error - no severity or no standard and no product')
            exit

    except Exception as e:
        print('Error: Get findings from event and send to FtCommonServiceNow()-', e)
        lambda_result = except_reason

    except ClientError as e:
        ClientError_reason = e.response['Error']['Code']
        print("ClientError_reason is: ", ClientError_reason)
        except_reason = "ClientError in dxcms_sec_hub_to_service_now"


def describe_policy_response(lambda_log_group_name,sh_to_snow_loggroup_retention,tries):
    try:
        put_retention_policy_response = log_client.put_retention_policy(
            logGroupName=lambda_log_group_name,
            retentionInDays=sh_to_snow_loggroup_retention
        )
    except ClientError as exception_obj:
        if exception_obj.response['Error']['Code'] == 'ThrottlingException':
            if tries <= 5:
                print("Throttling Exception Occured.")
                print("Retrying.....")
                print("Attempt No.: " + str(tries))
                sleep(3*tries)
                return describe_policy_response(lambda_log_group_name,sh_to_snow_loggroup_retention,tries + 1)
            else:
                print("Attempted 5 Times But No Success.")
                print("Raising Exception.....")
                raise
        else:
            raise
    return put_retention_policy_response

def get_findings_from_event(input_severity_list, input_standards_substring_list, input_integrations_list, event):
    get_findings_from_event_response = {'all_findings_obj': None, 'reason': None}
    except_reason = None
    try:
        # pull out only desired standards and desired integrations with desired severities
        desired_finding_list = []
        print("event in get_findings_from_event is: ", event)
        event_finding_list = event['detail']['findings']
        print("event_finding_list in get_findings_from_event is: ", event_finding_list)

        for onefinding in event_finding_list:
            finding_workflow_status = onefinding['Workflow']['Status']
            print("finding_workflow_status in get_findings_from_event is: ",  finding_workflow_status)
            findingId = onefinding['Id']
            print("Id in get_findings_from event is: ", findingId)
            findingProductArn = onefinding['ProductArn']
            print("findingProductArn in get_findings_from event is: ", findingProductArn)
            finding_sev = onefinding['Severity']['Label']
            print("finding_sev in get_findings_from event is: ", finding_sev)
            desired_finding_list = []

            std_exists = None
            for std in input_standards_substring_list:
                if std in findingId:
                    std_exists = True
                    break
            prod_exists = None
            for prod in input_integrations_list:
                if prod in findingProductArn:
                    prod_exists = True
                    break

            if (finding_sev in input_severity_list and finding_workflow_status == 'NEW' and (std_exists or prod_exists)):
                desired_finding_list.append(onefinding)

    except Exception as e:
        print('Error:get_findings_from_event()-', e)
        except_reason = "Exception error in get_findings_from_event"

    if except_reason is not None:
        get_findings_from_event_response['reason'] = except_reason
        return get_findings_from_event_response
    else:
        get_findings_from_event_response['all_findings_obj'] = desired_finding_list
        get_findings_from_event_response['reason'] = 'SUCCESS'
        print("success in get_findings_from_event, returning get_findings_from_event_response: ", get_findings_from_event_response) 
        return get_findings_from_event_response



def xlat_StandardsArn_to_search_substring(CompleteStandardsArn_list):
    xlat_StandardsArn_to_search_substring_response = {'substring_list': None, 'reason': None}
    except_reason = None
    try:
        substring_tmp_list = []
        for OneArn in CompleteStandardsArn_list:
            int_std_arn = OneArn
            if 'standards' in int_std_arn:
                split_on = 'standards'
            elif 'ruleset' in int_std_arn:
                split_on = 'ruleset'
            else:
                raise Exception('unknown StandardsArn type')
        
            tmp_list = OneArn.split(split_on)
            suffix = tmp_list[1]
            substring_tmp_list.append(suffix)
        
        print("substring_tmp_list is: ", substring_tmp_list)

    except Exception as e:
        print('Error:xlat_StandardsArn_to_search_substring()-', e)
        except_reason = "Exception error in xlat_StandardsArn_to_search_substring"

    if except_reason is not None:
        xlat_StandardsArn_to_search_substring_response['reason'] = except_reason
        return xlat_StandardsArn_to_search_substring_response
    else:
        xlat_StandardsArn_to_search_substring_response['substring_list'] = substring_tmp_list
        xlat_StandardsArn_to_search_substring_response['reason'] = 'SUCCESS'
        print("success in xlat_StandardsArn_to_search_substring, returning xlat_StandardsArn_to_search_substring_response: ", xlat_StandardsArn_to_search_substring_response) 
        return xlat_StandardsArn_to_search_substring_response

 
def set_workflow_status(finding, target_wf_status):
    # finding is a single finding, get the Id and ProductArn, then set desired status
    set_workflow_status_response = None
    except_reason = None
    try:
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
    except Exception as e:
        print('Error:set_workflow_status()-', e)
        except_reason = "Exception error in set_workflow_status"
    except ClientError as e:
        ClientError_reason = e.response['Error']['Code']
        print("ClientError_reason is: ", ClientError_reason)
        except_reason = "ClientError in set_workflow_status"

    if except_reason is not None:
        set_workflow_status_response = except_reason
        return set_workflow_status_response
    else:
        set_workflow_status_response = 'SUCCESS'
        print("success in set_workflow_status, returning set_workflow_status_response: ", set_workflow_status_response) 
        return set_workflow_status_response

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
    formatMessage_response = {'formatted_snow_message': None, 'email_subject': None, 'reason': None} 
    print("Building json to send to FtCommonServiceNow")
    if finding['ProductFields']['aws/securityhub/ProductName']:
        prod_name = finding['ProductFields']['aws/securityhub/ProductName']
    else:
        prod_name = 'Third party product'

    short_description = 'AWS ' + prod_name + ' finding ' + finding['Title']
    print("short_description in formatMessage is: ", short_description)
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
                "NewStateReason": short_description,
                "AWSAccountId": finding['AwsAccountId'],
                "NewStateValue": "ALARM",
                "correlation_id": finding['Id'],
                "InstanceId": finding['Id'],        
                "eventsourcesendingserver": "feature__security_hub",
                "eventsourceexternalid": event['id'],
                "title" : short_description,
                "longDescription": finding['Description'],
                "application" : finding['ProductArn'],
                "eventsourcecreatedtime" : event['time'],
                "PriorityData" : {
                    "Priority" : get_db_object()
                }
            }
            ]
        } 
        eventMsg['eventData'] = finding
        eventMsg['err'] = None

        # Format the payload to send to SNS
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
        formatMessage_response['email_subject'] = short_description
        formatMessage_response['reason'] = 'SUCCESS'
        print("formatMessage_response in formatMessage is: ", formatMessage_response) 
        return formatMessage_response


def send_to_FtCommonServiceNow(snow_message, topic_arn, email_subject):
    except_reason = None
    print("email_subject in send_to_FtCommonServiceNow is: ", email_subject)
    try:
        print("sending Security Hub findings to FtCommonServiceNow via SNS")
        print("snow_message in send_to_FtCommonServiceNow is: ", snow_message)
        sns_client_response = sns_client.publish(
            MessageStructure='json',
            Message=json.dumps(
                        {'default': json.dumps(snow_message)}
                    ),
            Subject=email_subject[:95],
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
