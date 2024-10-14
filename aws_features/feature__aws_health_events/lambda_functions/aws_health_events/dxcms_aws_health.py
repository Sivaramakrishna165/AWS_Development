import boto3
import logging
import os
import json
import http.client
import urllib3
from botocore.exceptions import ClientError
from botocore.config import Config
from http.client import responses
logger = logging.getLogger()
logger.setLevel(logging.INFO)


config=Config(retries=dict(max_attempts=10,mode='standard'))
sns_client = boto3.client('sns')
dynamodb_resource = boto3.resource('dynamodb', config=config)
feature_table='AccountFeatureDefinitions'
sns_client = boto3.client('sns')

priority = {'1': 'critical', '2': 'major', '3': 'minor', '4':'warning', '5':'ok'}

### Environment variables from CFT
stack_region = os.environ['STACK_REGION']
execution_account = os.environ['EXECUTION_ACCOUNT']
servicenow_topic=os.environ['servicenow_topic']

###  Note: e-mail does not meet MSP audit requirements and is not included in this version, but may be added for Silver accounts in a future version.
###       Health event payload is sent to feature Common Servicenow which will send to ServiceNow

def lambda_handler(event, context):

    print('Received Event:',event)

     #Fetch priorities
    all_events_prority,risk_event_priority=fetch_priority()
    ### Process the event 

    formatMessage_result = formatMessage(event,all_events_prority,risk_event_priority)
    send_to_com_ServiceNow(
        formatMessage_result['formatted_API_message'])

def fetch_priority():
    try:
        table = dynamodb_resource.Table(feature_table)
        response = table.get_item(Key={"Feature":"AWSHealthEvents"})
        all_events_prority = response['Item']['FeatureParams']['pAllEventsPriority']['Default']
        risk_event_priority = response['Item']['FeatureParams']['pRiskEventsPriority']['Default']

        return all_events_prority,risk_event_priority

    except Exception as e:

        print("Error-getting priority-",e)

    formatMessage_result = formatMessage(event)
    send_to_com_ServiceNow(
        formatMessage_result['formatted_API_message'])



def formatMessage(event,all_events_prority,risk_event_priority):
    # Build the eventMsg to send to ServiceNow via Agnostic API, will not work with SNS topic. After the ServiceNow event is created, an incident will be created
    except_reason = None
    formatMessage_response = {'formatted_API_message': None, 'reason': None} 
    print("Building json to send to ServiceNow")
    event_id = event['id']
    event_detail_service = event['detail']['service']
    event_detail_eventTypeCategory = event['detail']['eventTypeCategory']
    event_detail_type = event['detail-type']
    event_source = event['source']
    event_account = event['account']
    event_time = event['time']
    event_region = event['region']
    event_detail_dict = event['detail']
    valid_health_risk_event = ((event_detail_type == 'AWS Health Event') and
                               (event_source == 'aws.health') and
                               (event_detail_service == 'RISK') and
                               (event_detail_eventTypeCategory == 'issue')
                              )
        
    short_description = 'AWS Health Event '+ event_detail_service + ' AWS Account: ' + event_account + ' Event ID: ' + event_id
    alert_reason = event_detail_dict 
    incident_app = event_detail_type + ' EventAccount: ' + event_account + ' EventRegion ' +  event_region + ' Service: ' + event_detail_service
    # Notes:
    #  Severity and Impact must result in a ServiceNow P1 Incident,  per MSP Audit V4.2 section 8.2.4 to create ticket at highest severity 
    #  severity and impact determine ServiceNow incident priority
    #  Agnostic API docs: https://github.dxc.com/Platform-DXC/event-mgmt/blob/master/docs/EventAgnosticApi.md#CreateEvtJson
    #  title is also used for ServiceNow de-dup while creating incidents
    #  using event_id as part of the short description ensures a new ServiceNow incident for each new AWS Health risk event

    try:
        
        if valid_health_risk_event: 
            incidentSeverity = priority[risk_event_priority]
            findingIncidentImpact = risk_event_priority
        else:
            incidentSeverity = priority[all_events_prority]
            findingIncidentImpact = all_events_prority
        incidentTitle = short_description
        incidentLongDescription = alert_reason
        incidentEventSourceSendingServer = 'Feature_AWS_Health_events'
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
                "incidentImpact": findingIncidentImpact,
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

def send_to_com_ServiceNow(api_message):
    except_reason = None
    try:
        print("api_message is:",api_message)
        sns_client.publish(TopicArn=servicenow_topic, Message=api_message) 
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
