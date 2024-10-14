import boto3
import logging
import os
import json
import http.client
import urllib3
from botocore.exceptions import ClientError
from http.client import responses
from botocore.config import Config

logger = logging.getLogger()
logger.setLevel(logging.INFO)

config=Config(retries=dict(max_attempts=10,mode='standard'))
trail_client = boto3.client('cloudtrail', config=config)
sns_client = boto3.client('sns', config=config)
dynamodb_resource = boto3.resource('dynamodb', config=config)
feature_table='AccountFeatureDefinitions'

priority = {'1': 'critical', '2': 'major', '3': 'minor', '4':'warning', '5':'ok'}

### Note: until existence of the common sns topic e-mail can be determined during CFT creation, 
###   e-mail is optional and Agnostic API creds are mandatory 

def lambda_handler(event, context):

    print("event is ", event)

    ### Environment variables from CFT

    stack_region = os.environ['STACK_REGION']
    execution_account = os.environ['EXECUTION_ACCOUNT']
    sns_email_topic_arn = os.environ['SNS_EMAIL_TOPIC']
    servicenow_topic=os.environ['servicenow_topic']
    number_of_trails = os.environ['NUMBER_OF_TRAILS']

    #Fetch priorities
    incident_impact=fetch_priority()
    incident_severity=priority[incident_impact]

    ### Get list of CloudTrails in each region 

    try:
        print("Retrieving list of CloudTrails")
        list_trails_response = {}
        list_trails_response['Trails'] = []
        args = {}
        header_date = ''
        while(True):
            response = trail_client.list_trails(**args)
            header_date = response['ResponseMetadata']['HTTPHeaders']['date']
            for trail in response['Trails']:
                trail_client_region = boto3.client('cloudtrail', region_name = trail['HomeRegion'], config=config)
                response_status = trail_client_region.get_trail_status(Name = trail['TrailARN'])
                is_logging = response_status['IsLogging']
                if(is_logging):
                    print('Trail - "{}" is ENABLED'.format(trail['Name']))
                    list_trails_response['Trails'].append(trail)
                else:
                    print('Trail - "{}" is DISABLED'.format(trail['Name']))
            
            if 'NextToken' in response:
                args['NextToken'] = response['NextToken']
            else:
                break
        print("list_trails_response in lambda handler is: ", list_trails_response)

    except Exception as e:
        print('Error:Retrieving list of CloudTrails()-', e)
        except_reason = "Exception error in Retrieving list of CloudTrails"
    except ClientError as e:
        ClientError_reason = e.response['Error']['Code']
        print("ClientError_reason is: ", ClientError_reason)
        except_reason = "ClientError in Retrieving list of CloudTrails"

    ### If the global CloudTrail does not exist in us-east-1, 
    ###    create a ServiceNow incident using Agnostic API
    ###    send an e-mail notification using Common SNS Topic

    trail_list = list_trails_response['Trails']
    print("ENABLED trail_list is", trail_list)
    print(" ")
    global_cloudtrail_exists = False
    for trail in trail_list:
        if 'cloudtrail-global' in trail['Name']  and trail['HomeRegion'] == 'us-east-1':
            global_cloudtrail_exists = True
            break
    
    if not global_cloudtrail_exists:
        print("creating ServiceNow ticket for no global cloudtrail")
        alert_reason = 'logs-cloudtrail-global stack does not exist in us-east-1'
        formatMessage_result = formatMessage(list_trails_response,stack_region,execution_account,alert_reason,incident_severity,incident_impact, header_date)
        send_to_ServiceNow_result = send_to_ServiceNow(
            formatMessage_result['formatted_API_message'],
            servicenow_topic
        )
        print("sending e-mail via common sns topic lambda function")
        try:
            send_email_result = send_email(
                formatMessage_result['formatted_sns_message'],
                sns_email_topic_arn,
                formatMessage_result['email_subject'],
                ) 
        except Exception as e:
            print('Error:calling email()-', e)
            except_reason = 'Error in lambda handler calling send_email' 

    ### If more than number_of_trails CloudTrail trails exists in the account, this is a cost issue, 
    ###    create a ServiceNow incident using Agnostic API
    ###    send an e-mail notification using Common SNS Topic

    if len(trail_list) > int(number_of_trails):
        print("too many CloudTrail trails, alerting ServiceNow")
        alert_reason = 'too many CloudTrail trails exist in ' + execution_account
        formatMessage_result = formatMessage(list_trails_response,stack_region,execution_account,alert_reason,incident_severity,incident_impact, header_date)
        send_to_ServiceNow_result = send_to_ServiceNow(
            formatMessage_result['formatted_API_message'],
            servicenow_topic
        )
        print("sending e-mail via common sns topic lambda function")
        try:
            send_email_result = send_email(
                formatMessage_result['formatted_sns_message'],
                sns_email_topic_arn,
                formatMessage_result['email_subject'],
                ) 
        except Exception as e:
            print('Error:calling email()-', e)
            except_reason = 'Error in lambda handler calling send_email' 

def formatMessage(list_trails_response,stack_region,execution_account,alert_reason,incident_severity,incident_impact, header_date):
    # Build the eventMsg to send to ServiceNow via Agnostic API, will not work with SNS topic. After the ServiceNow event is created, an incident will be created
    # Build the e-mail subject to send to SNS topic
    except_reason = None
    formatMessage_response = {'formatted_sns_message': None,'formatted_API_message': None, 'email_subject': None, 'reason': None} 
    print("Building json to send to ServiceNow")
    if "logs-cloudtrail-global" in alert_reason:
        short_description = 'GlobalCloudtrailHealth logs-cloudtrail-global issue in ' + execution_account
    elif "too many" in alert_reason:
        short_description = 'GlobalCloudtrailHealth too many trails issue in ' + execution_account
    print("short_description in formatMessage is: ", short_description)

    try:
        print("list_trails_response in formatMessage is: ", list_trails_response)
        
        incidentSeverity = incident_severity
        ###  title is also used for ServiceNow de-dup while creating incidents
        incidentTitle = short_description
        incidentLongDescription = alert_reason
        incidentEventSourceSendingServer = 'GlobalCloudtrailHealth lambda function'
        incidentEventSourceExternalid = 'dxcms-global-cloudtrail-health'
        incidentCreateDt =  header_date
        incidentApplication = 'dxcms-global-cloudtrail-health-' + stack_region
        incidentCategory = "AWS Monitoring"
        findingIncidentCategory = "Integration"
        findingIncidentSubcategory = "Data"
        findingIncidentImpact = incident_impact

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

        # Format message for sending to common SNS topic
        message = '{"Issue":' + '"' + short_description + '"' + '}'

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
        formatMessage_response['formatted_sns_message'] = snsJsonMsg
        formatMessage_response['formatted_API_message'] = ApiEventMsg
        #formatMessage_response['email_subject'] = short_description[:100]
        formatMessage_response['email_subject'] = incidentLongDescription
        formatMessage_response['reason'] = 'SUCCESS'
        print("formatMessage_response in formatMessage is: ", formatMessage_response) 
        return formatMessage_response

def send_email(sns_message, sns_email_topic_arn, email_subject):
        try:
            ### Send to common SNS topic lambda which will send to a topic with an e-mail subscription
            print("sns_message_before_changing is ", sns_message)
            sns_publish_response = sns_client.publish(
                MessageStructure='json',
                Message=sns_message,
                Subject=email_subject,
                TopicArn=sns_email_topic_arn
            )
            print("sns_publish_response is: ", sns_publish_response)
        except Exception as e:
            print('Error:send_email()-', e)
            except_reason = 'Error in send_email' 

def send_to_ServiceNow(api_message, servicenow_topic):
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

def fetch_priority():
    try:
        table = dynamodb_resource.Table(feature_table)
        response = table.get_item(Key={"Feature":"GlobalCloudtrailHealth"})
        incident_priority = response['Item']['FeatureParams']['pIncidentsPriority']['Default']
        return incident_priority
    except Exception as e:
        print("Error-getting priority-",e)