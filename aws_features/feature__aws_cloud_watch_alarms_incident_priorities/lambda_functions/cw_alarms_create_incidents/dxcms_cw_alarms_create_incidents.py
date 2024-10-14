'''
Lambda function is invoked on any Alarm breach.
Trigger from the Topics     
    'DXCMS-CW-Alarms-Create-Incidents-P1'
    'DXCMS-CW-Alarms-Create-Incidents-P3'
    'DXCMS-CW-Alarms-Create-Incidents-P2'
    'DXCMS-CW-Alarms-Create-Incidents'

Assign the Priority to the alarm and sends the payload to CommonServiceNow solution

'''

import boto3
import operator
import logging
import os
import json
#import ast
from botocore.config import Config
logger = logging.getLogger()
logger.setLevel(logging.INFO)


config=Config(retries=dict(max_attempts=10,mode='standard'))
sns_client = boto3.client('sns', config=config)
dynamodb_resource = boto3.resource('dynamodb', config=config)
dynamodb_client = boto3.client('dynamodb', config=config)
ssm_client = boto3.client('ssm',config=config)

priority_toipcs = {
    'DXCMS-CW-Alarms-Create-Incidents-P1':'P1',
    'DXCMS-CW-Alarms-Create-Incidents-P2':'P2',
    'DXCMS-CW-Alarms-Create-Incidents-P3':'P3',
    'DXCMS-CW-Alarms-Create-Incidents':'FetchPriority'
}

operators = {'Greater': 'ge',
             'Less': 'le'
            }

ec2_name_spaces = ['Windows/Default', 'AWS/EC2', 'CWAgent']


### Environment variables from CFT
stack_region = os.environ['STACK_REGION']
execution_account = os.environ['EXECUTION_ACCOUNT']
cw_alarms_ddb = os.environ['CWAlarmsDDB']
customer_name = os.environ['CustomerName']
servicenow_topic=os.environ['servicenow_topic']
business_service_param=os.environ["Business_service"]
priority = None

def handler(event, context):
    try:
        print('Received Event:',event)
        if (len(event['Records']) != 1):
            print('Expected only one record ',event)
            print("FAILURE")
        else:
            print("############### PAYLOAD EVENT ####################")
            print(event)
            print("############### PAYLOAD EVENT ####################")
            notification = event['Records'][0]['Sns']
            message = json.loads(notification['Message'])
            messageKey = message['AlarmName']
            
            # If the Trigger is not in event, then its not an Alarm. Return None
            if('Trigger' not in message):
                print('Trigger Not available in the event')
                print('Event is Not an Alarm, so skipping sending to SNOW')
                return None
                
            event_metric_name = message['Trigger']['MetricName']
            event_Namespace = message['Trigger']['Namespace']
            message_dimensions = message['Trigger']['Dimensions']
            compare_operator = message['Trigger']['ComparisonOperator']
            
            instance = next((sub for sub in message_dimensions if sub['name'] == 'InstanceId'), None)
            if instance:
                messageKey += '_'+instance['value']

            device = next((sub for sub in message_dimensions if sub['name'] == 'device'), None)
            if device:
                messageKey += '_' + device['value']
            
            print('Message key: ', messageKey)
            print('Alarm state: ', message['NewStateValue'])
            
            snstopic = notification["TopicArn"]
            print(snstopic)

            for topic_name in priority_toipcs:
                if topic_name in snstopic:
                    priority = priority_toipcs[topic_name]
                    break
            
            print('Priority', priority)
            # If coming from Different SNS Topic the by default P3 is set
            if priority == None:
                priority = 'P3'
            
            dynamo_items = []
            # Fetch the Priority from DDB table
            if priority == 'FetchPriority':
                if(event_Namespace in ec2_name_spaces):
                    event_Namespace = 'AWS/EC2'
                service_metric_key =  "-".join([event_Namespace.split('/')[-1], "".join(event_metric_name.split()), 'Static'])
                print('service_metric_key - ', service_metric_key)
                for item in scan_table():
                    # print(item)
                    if(service_metric_key in item['Service-Metric-Priority']):
                        dynamo_items.append(item)
                
                print('Priorities and Thresholds in dynamodb', dynamo_items)
            
            if(len(dynamo_items)>0):
                thresholds = []
                for item in dynamo_items:
                    thresholds.append(item['Threshold'])
                if('Greater' in compare_operator):
                    thresholds.sort(reverse=True)
                else:
                    thresholds.sort(reverse=False)
                map_threshold = get_threshold(compare_operator, message['Trigger']['Threshold'], thresholds)
                print('Mapped Threshold', map_threshold)
                if(map_threshold):
                    for item in dynamo_items:
                        if(item['Threshold'] == map_threshold):
                            print('Service-Metric-Priority "{}"'.format(item['Service-Metric-Priority']))
                            priority = item['Service-Metric-Priority'].split('-')[-1]
                else:
                    priority = 'P3'
            elif priority not in ['P1','P2','P3']:
                priority='P3'
                
            print(priority)
            
            formatMessage_result = formatMessage(event, priority)
            print(formatMessage_result)
            send_to_com_ServiceNow(
                formatMessage_result['formatted_API_message'])

    except Exception as e:
        print('Lambda execution Error - ',e)
        raise


def get_threshold(compare_operator, alarm_threshold, thresholds):
    th_map_list = {}
    for th in thresholds:
        th_map_list[float(th)] = th
    thresholds = [float(th) for th in thresholds]
    if('Greater' in compare_operator):
        op = 'Greater'
        thresholds.sort(reverse=True)
    else:
        op = 'Less'
        thresholds.sort(reverse=False)
        
    print(op)
    print(thresholds)
    for th in thresholds:
        # if('Greater' in compare_operator):
        #bln = eval(f"operator.{operators[op]}({alarm_threshold},{th})")
        # bln = ast.literal_eval(f"operator.{operators[op]}({alarm_threshold},{th})")
        bln = getattr(operator, operators[op])(alarm_threshold, th)
        # else:
            # bln = eval(f"operator.{operators[compare_operator]}({alarm_threshold})")
        # print(bln)
        print(bln)
        if(bln):
            return th_map_list[th]

def scan_table():
    try:
        table = dynamodb_resource.Table(cw_alarms_ddb)
        done = False
        start_key = None
        scan_kwargs  = {}
        # check for pagination key, if present make another scan for next page
        while not done:
            if start_key:
                scan_kwargs['ExclusiveStartKey'] = start_key
            response = table.scan(**scan_kwargs)
            start_key = response.get('LastEvaluatedKey', None)
            
            # ensure there's data and fetch another page
            data = response['Items']
            if data:
                # iterate through each result in the page
                for item in data:
                    yield item
    
            done = start_key is None
            
    except Exception as e:
        print("Error - scan_table()",e)
        raise

def formatMessage(event,priority):
    except_reason = None
    formatMessage_response = {'formatted_API_message': None, 'reason': None} 
    print("Building json to send to ServiceNow")
    sns_message     = json.loads(event['Records'][0]['Sns']['Message'])
    sns_message_id  = event['Records'][0]['Sns']['MessageId']
    sns_topic       = event['Records'][0]['Sns']['TopicArn'].split(sep=":")[-1]
    aws_account_id  = event['Records'][0]['Sns']['TopicArn'].split(sep=":")[4]
    aws_region      = event['Records'][0]['Sns']['TopicArn'].split(sep=":")[3]
    event_timestamp   = event['Records'][0]['Sns']['Timestamp']
    if "AlarmName" in sns_message.keys():
        message_source_type = "AWS CloudWatch"
    
    # Retrieve CloudWatchAlarm specific details - will overwrite some SNS topic derived values
    if message_source_type == "AWS CloudWatch":
        aws_account_id = sns_message['AWSAccountId']
        aws_region     = sns_message['AlarmArn'].split(":")[3]
        if('Dimensions' in sns_message['Trigger']):
            try:
                aws_resource_id = sns_message['Trigger']['Dimensions'][0]['value']
            except:
                aws_resource_id = ''
        else:
            aws_resource_id = ''
        for name in sns_message['Trigger']['Dimensions']:
            if (name['name'] == 'InstanceId') or (name['name'] == 'LoadBalancer') or (name['name'] == 'DBInstanceIdentifier') or (name['name'] == 'DBClusterIdentifier') :
                aws_resource_id = name['value']
        alarm_name      = sns_message['AlarmName']
        event_timestamp   = sns_message['StateChangeTime']    
        metric_name = sns_message['Trigger']['MetricName']

        # Format Short Description field
        formatted_short_description = "AWS CloudWatch - [" + customer_name +"] - [" + aws_account_id + "]- ["+ aws_region + "] "

        if aws_resource_id != "" :
            if sns_topic.find(aws_resource_id) < 0 :
                formatted_short_description = formatted_short_description + "Resource  - " + aws_resource_id + " - " + alarm_name
                object = aws_resource_id
        else:
            formatted_short_description = formatted_short_description + alarm_name

        # Format Long Description field
        formatted_long_description = "AWSAccountId: " + aws_account_id + " ; "
        formatted_long_description = formatted_long_description + "Region: " + aws_region + " ; "

        if aws_resource_id != "" :
            try:
                formatted_long_description = formatted_long_description + "Resource ID: " + aws_resource_id + " ; "
            except Exception:
                pass

        try:
            formatted_long_description = formatted_long_description + "Namespace (Resource type): " + sns_message['Trigger']['Namespace'] + " ; "
        except Exception:
            pass

        try:
            formatted_long_description = formatted_long_description + "AlarmName: " + alarm_name + " ; "
        except Exception:
            pass
        
        try:
            formatted_long_description = formatted_long_description + "AlarmDescription: " + sns_message['AlarmDescription'] + " ; "
        except Exception:
            pass
        
        try:
            formatted_long_description = formatted_long_description + "MetricName: " + sns_message['MetricName'] + " ; "
        except Exception:
            pass

        try:    
            formatted_long_description = formatted_long_description + "NewStateValue: " + sns_message['NewStateValue'] + " ; "
        except Exception:
            pass

        try:    
            formatted_long_description = formatted_long_description + "NewStateReason: " + sns_message['NewStateReason'] + " ; "
        except Exception:
            pass

        try:    
            formatted_long_description = formatted_long_description + "StateChangeTime: " + sns_message['StateChangeTime'] + " ; "
        except Exception:
            pass
        
        try:    
            formatted_long_description = formatted_long_description + "Threshold: " + sns_message['Threshold'] + " ; "
        except Exception:
            pass
    
        incident_app = message_source_type + ' EventAccount: ' + aws_account_id + ' EventRegion ' +  aws_region + ' Service: ' + alarm_name
   
    # Message source is neither from CloudWatch Alarm nor GuardDuty
    else:
        formatted_short_description = "[AWS][" + customer_name +"][" + aws_account_id + "]["+ aws_region + "] " + event['Records'][0]['Sns']['Subject']
        formatted_long_description = sns_message
    
    severity  = "minor"
    incidentImpact = "3"

    if priority == 'P1':
        severity = "critical"
        incidentImpact = "1"
    elif priority == 'P2' :
        severity = "major"
        incidentImpact = "2"
    elif priority == 'P3':
        severity = "minor"
        incidentImpact = "3"
    
    try:
        incidentSeverity = severity
        findingIncidentImpact = incidentImpact
        incidentTitle = formatted_short_description
        incidentLongDescription = formatted_long_description
        incidentEventSourceSendingServer = 'Feature-DXCMS-CW-Alarms-Create-Incidents'
        incidentEventSourceExternalid = sns_message_id
        incidentCreateDt =  event_timestamp
        incidentApplication = incident_app
        incidentCategory = "AWS Monitoring"
        findingIncidentCategory = "Hardware"
        findingIncidentSubcategory = "Midrange/Server Failure"
        businessService = get_param_value(business_service_param)

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
                "BizSrvc_CI_Name": businessService,
                "custompairs": [
                    {
                        "name" : "AWSAccountId",
                        "value": aws_account_id,
                }],
                "PriorityData": {
                    "Priority": findingIncidentImpact
                }
            }    
            ] 
        }

        # if e-mail is configured, message is the e-mail body, sent via common SNS topic
        message = formatted_short_description
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

def get_param_value(param):
    try:
        response = ssm_client.get_parameter(Name=param)
        return response['Parameter']['Value']
    except Exception as e:
        print("Error-get_param_value()",e)
        
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
