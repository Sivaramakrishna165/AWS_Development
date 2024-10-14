'''
Detect CFT Drift class helps to retrieves all the drifted resources
in all the Cloudformations available in region.
NOTE: Drift detect is applicable for the stack status ['CREATE_COMPLETE','UPDATE_COMPLETE', 'UPDATE_ROLLBACK_COMPLETE']
CFT Status with Failed/InProgress cannot be processed for drift detect
 Expected event for lambda to run DetectStackDrift - {"RequestType":"DetectStackDrift"}
                                  ViewStackDrift - {"RequestType":"ViewStackDrift"}
'''

import logging
import os
import json
import http.client
import urllib3
from datetime import datetime
from botocore.exceptions import ClientError
from http.client import responses
from boto_helper import boto_helper

logger = logging.getLogger()
logger.setLevel(logging.INFO)
helper_obj = boto_helper()

priority = {'1': 'critical', '2': 'major', '3': 'minor', '4':'warning', '5':'ok'}
const_no_value = 'AWSMS-NoValue'
view_drifts_rule = 'AWSMS-ViewStackDrifts'
### Environment variables from CFT
stack_region = os.environ['STACK_REGION']
execution_account = os.environ['EXECUTION_ACCOUNT']
servicenow_topic = os.environ['servicenow_topic']
sns_topic = os.environ['DetectDriftTopic']
ssm_param_whitelst = os.environ['SSMParamWhiteListCft']
ssm_param_whitelst_res = os.environ['SSMParamWhiteListResources']

###  Note: e-mail does not meet MSP audit requirements and is not included in this version, but may be added for Silver accounts in a future version.
###        Agnostic API creds are mandatory 

def lambda_handler(event, context):
    try:
        # TODO: write code...
        print('Received Event:',event)
        if('RequestType' in event and 
                event['RequestType'] in ['DetectStackDrift', 'ViewStackDrift']):

            request_type = event['RequestType']
            context_id = context.aws_request_id
            whitelisted_stacks = helper_obj.get_ssm_param_values(ssm_param_whitelst).split(',')
            whitelisted_stacks = [x.strip() for x in whitelisted_stacks]
            
            whitelisted_resources = helper_obj.get_ssm_param_values(ssm_param_whitelst_res).split(',')
            whitelisted_resources = [x.strip() for x in whitelisted_resources]
            
            if(const_no_value not in whitelisted_stacks): print('Whitelisted Stack Names - ',whitelisted_stacks)
            if(const_no_value not in whitelisted_resources): print('Whitelisted Resource Names - ',whitelisted_resources)
            
            stack_names = helper_obj.get_all_stacks()
            print('All stack names - ', stack_names)

            #Filter - Get Managed stacks
            managed_stacks = helper_obj.get_managed_stacks(stack_names)
            print('Managed stack names - ', managed_stacks)

            # Filter the stacks
            filtered_stacks = list(filter(lambda x : x not in whitelisted_stacks, managed_stacks))
            print('Detecting drift for stacks - ',filtered_stacks)
            
            #Process start to Detect CFT Drift
            drifted_stacks_lst = []
            drifted_resources_lst = []
            for stack in filtered_stacks:
                drifted_resources = []
                if(request_type == 'DetectStackDrift'):
                    helper_obj.detect_drift(stack)
                if(request_type == 'ViewStackDrift'):
                    drifted_resources = helper_obj.describe_stack_resource_drifts(stack_name=stack, white_listed_resources=whitelisted_resources)
                    if drifted_resources:
                        drifted_stack = {}
                        drifted_stack['StackName'] = stack
                        drifted_stack['DriftedResources'] = drifted_resources
                        drifted_stacks_lst.append(drifted_stack)
                        drifted_resources_lst.extend(drifted_resources)
                        # break
            # Enable the "AWSPE-ViewStackDrift" Rule for Detect to invoke the lambda after 15mins
            if(request_type == 'DetectStackDrift'):
                print('Executed DetectStackDrift on Cloudformations')
                helper_obj.enable_event_rule(view_drifts_rule)
                print('Enabled rule ',view_drifts_rule)

            ### Process the event
            if(drifted_stacks_lst and request_type == 'ViewStackDrift'):
                print('Drifted Stacks & Resources - ', drifted_stacks_lst)
                print('Executed ViewStackDrifts on Cloudformations')
                now = datetime.now()
                event_priority = helper_obj.fetch_priority()
                testevent = {
                      "version": "0",
                      "id": context_id,
                      "detail-type": "AWS Detect CFT Drift",
                      "source": "aws.cloudformation",
                      "account":execution_account,
                      "time": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                      "region": stack_region,
                      "resources": [],
                      "detail": {
                        "check-name": "Cloudformations drifts",
                        "check-item-detail": {
                          "Drifted-Stacks":drifted_stacks_lst
                        },
                        "status": (priority[event_priority]).upper(),
                        "resource_id": context.invoked_function_arn,
                        "uuid": context_id
                      }
                    }                
                formatMessage_result = formatMessagetest(testevent,event_priority)
                send_to_ServiceNow_result = send_to_ServiceNow(
                    formatMessage_result['formatted_API_message']
                )
                if(sns_topic != const_no_value):
                    helper_obj.publish_to_topic(sns_topic, drifted_stacks_lst, execution_account, stack_region)
                
                # Disable the "AWSPE-ViewStackDrift" after sending the notification
                helper_obj.disable_event_rule(view_drifts_rule)
                print('Disabled rule ',view_drifts_rule)

        else:
            print('Invalid event. Does not have proper RequestType')
    except Exception as e:
        raise e

def formatMessagetest(event,event_priority):
    # Build the eventMsg to send to ServiceNow via Agnostic API, will not work with SNS topic. After the ServiceNow event is created, an incident will be created
    except_reason = None
    formatMessage_response = {'formatted_API_message': None, 'reason': None} 
    print("Building json to send to ServiceNow")

    event_id = event['id']
    event_detail_chk_name = event['detail']['check-name']
    event_detail_status = event['detail']['status']
    event_detail_type = event['detail-type']
    event_source = event['source']
    event_account = event['account']
    event_time = event['time']
    event_region = event['region']
    event_resources_list = event['resources']
    event_detail_dict = event['detail']
        
    short_description = 'AWS Detect CFT Drifts ' + event_detail_status + ' AWS Account: ' + event_account + ' Event ID: ' + event_id
    alert_reason = event_detail_dict 
    incident_app = event_detail_type + ' EventAccount: ' + event_account + ' EventRegion ' +  event_region + ' Status: ' + event_detail_status
    # Notes:
    #  severity and impact determine ServiceNow incident priority
    #  Agnostic API docs: https://github.dxc.com/Platform-DXC/event-mgmt/blob/master/docs/EventAgnosticApi.md#CreateEvtJson
    #  title is also used for ServiceNow de-dup while creating incidents
    #  using event_id as part of the short description ensures a new ServiceNow incident for each new AWS Health risk event

    try:
    
        incidentSeverity = priority[event_priority]
        findingIncidentImpact = event_priority
        incidentTitle = short_description
        incidentLongDescription = alert_reason
        incidentEventSourceSendingServer = 'dxcms-detect-cft-drifts lambda function'
        incidentEventSourceExternalid = event_id
        incidentCreateDt =  event_time
        incidentApplication = incident_app
        incidentCategory = "AWS Monitoring"
        findingIncidentCategory = "Integration"
        findingIncidentSubcategory = "Data"

        eventMsg = {
           "EventList":[
           {
             "eventsourcesendingserver": incidentEventSourceSendingServer,
             "eventsourceexternalid": incidentEventSourceExternalid,
             "severity": incidentSeverity,
             "title": incidentTitle,
             "longDescription": incidentLongDescription,
             "category": incidentCategory,
             "application": incidentApplication,
             "eventsourcecreatedtime": incidentCreateDt,
             "incidentCategory": findingIncidentCategory,
             "incidentSubcategory": findingIncidentSubcategory,
             "PriorityData": {
                    "Priority": findingIncidentImpact
                }
            }    
           ] 
        }

        # if e-mail is configured, message is the e-mail body, sent via common SNS topic
        message = short_description
        snsJson = {}
        snsJson['default'] = message
        snsJson['https'] = json.dumps(eventMsg)
        snsJsonMsg = json.dumps(snsJson)
        ApiEventMsg = snsJson['https']
        print("snsJsonMsg is: ", snsJsonMsg)
        print("type of snsJsonMsg is: ", type(snsJsonMsg))

    except Exception as e:
        print('Error:formatMessage()-', e)
        except_reason = 'Error in formatMessage' 

    if except_reason is not None:
        formatMessage_response['reason'] = except_reason
        return formatMessage_response
    else:
        formatMessage_response['formatted_API_message'] = ApiEventMsg
        formatMessage_response['reason'] = 'SUCCESS'
        print("formatMessage_response in formatMessage is: ", formatMessage_response) 
        return formatMessage_response
        

def send_to_ServiceNow(api_message):
    except_reason = None
    try:
        print("api_message is:",api_message)

        ### Publishing payload to common servicenow topic
        helper_obj.publish_to_topic(servicenow_topic, api_message, execution_account, stack_region,True)
        print("Message sent to common servicenow topic")
    except Exception as e:
        print('Error:send_to_ServiceNow()-', e)
        except_reason = 'Error in send_to_ServiceNow'
    except ValueError as err:
        print('ValueError:send_to_ServiceNow()-', err)
        except_reason = 'Error in send_to_ServiceNow'

    if except_reason is not None:
        return except_reason
    else:
        return 'SUCCESS'
