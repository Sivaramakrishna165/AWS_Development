"""
This lambda will be triggered by SNS. This gets triggered when ever CloudWatch Alarm is hit.
This function formats the incoming event to JSON format which is accepted by Service now
in order to create an incident. And also sends the event to email ID subscribed.
"""

import boto3
import json
import os
from botocore.config import Config


def prepare_json_message_for_snow(event):
   
   try:
      
      event_MessageId = event['Records'][0]['Sns']['MessageId']
      event_records = event['Records'][0]['Sns']['Message']
   
      event_records_fin = json.loads(event_records)
      # If the Trigger is not in event, then its not an Alarm. Return None
      if('Trigger' not in event_records_fin):
         return None
      event_metric_name = event_records_fin['Trigger']['MetricName']
      event_dimensions = event_records_fin['Trigger']['Dimensions']
      event_EvaluateLowSampleCountPercentile = event_records_fin['Trigger']['EvaluateLowSampleCountPercentile']
      event_ComparisonOperator = event_records_fin['Trigger']['ComparisonOperator']
      event_TreatMissingData = event_records_fin['Trigger']['TreatMissingData']
      event_Statistic = event_records_fin['Trigger']['Statistic']
      event_StatisticType = event_records_fin['Trigger']['StatisticType']
      event_Period = event_records_fin['Trigger']['Period']
      event_EvaluationPeriods = event_records_fin['Trigger']['EvaluationPeriods']
      event_Unit = event_records_fin['Trigger']['Unit']
      event_Namespace = event_records_fin['Trigger']['Namespace']
      event_Threshold = event_records_fin['Trigger']['Threshold']
      
      event_AlarmName = event_records_fin['AlarmName']
      event_AlarmDescription = event_records_fin['AlarmDescription']
      event_NewStateReason = event_records_fin['NewStateReason']
      event_AWSAccountId = event_records_fin['AWSAccountId']
      event_Region = event_records_fin['Region']
      event_OldStateValue = event_records_fin['OldStateValue']
      event_NewStateValue = event_records_fin['NewStateValue']
      print('reading nodes is done')
      
      formatMessage_response = {'formatted_snow_message': None, 'reason': None}
      eventMsg = {
         "Trigger": {
               "MetricName": event_metric_name,
               "Dimensions": event_dimensions,
            "EvaluateLowSampleCountPercentile": event_EvaluateLowSampleCountPercentile,
            "ComparisonOperator": event_ComparisonOperator,
            "TreatMissingData": event_TreatMissingData,
            "Statistic": event_Statistic,
            "StatisticType": event_StatisticType,
            "Period": event_Period,
            "EvaluationPeriods": event_EvaluationPeriods,
            "Unit": event_Unit,
            "Namespace": event_Namespace,
            "Threshold": event_Threshold
         },
         "AlarmName": event_AlarmName,
         "AlarmDescription": event_AlarmDescription,
         "NewStateReason": event_NewStateReason,
         "AWSAccountId": event_AWSAccountId,
         "Region": event_Region,
         "OldStateValue": event_OldStateValue,
         "NewStateValue": event_NewStateValue,
         "MessageId": event_MessageId,
         "PriorityData": {
            "Priority": get_priority()
        }
      }
      
      eventMsg['eventData'] = event
      eventMsg['err'] = None
      
      # Format the payload to send to SNS, https and e-mail
      message = """AWSMS Offerings alerts to ServiceNow via SNS. Please find the information below\n
      AWSAccountId : %s
      AlarmName : %s
      NewStateReason: %s
      Region : %s
      MetricName : %s
      Namespace : %s
      Dimensions : %s
      """ % (event_AWSAccountId,event_AlarmName,event_NewStateReason,
             event_Region,event_metric_name,event_Namespace,event_dimensions)
      snsJson = {}
      snsJson['default'] = json.dumps(eventMsg)
      snsJson['https'] = message
      snsJsonMsg = json.dumps(snsJson)
      
      formatMessage_response['formatted_snow_message'] = snsJsonMsg 
      formatMessage_response['reason'] = 'SUCCESS'

      return formatMessage_response
   
   except Exception as e:
        print('Error occurred in prepare_json_message_for_snow:',e)

def prepare_json_message_for_email(event):
   try:
            
      event_MessageId = event['Records'][0]['Sns']['MessageId']
      event_msg = event['Records'][0]['Sns']['Message']   
      event_msg = json.loads(event_msg)
      message = """AWSMS Offerings alerts via CommonSNS. Please find the information below\n"""
      snsJson = {}
      snsJson['default'] = message
      snsJson['email'] = json.dumps(event_msg)
      snsJsonMsg = json.dumps(snsJson)

      return snsJsonMsg
   except Exception as e:
      print('Error occurred in prepare_json_message_for_email:',e)

# Publish the message to sns
def publish_message(message, subscription_type):
    try:
         if subscription_type == 'email':
            snstopic = os.environ['snstopic']
            print('Publishing Notification for subscription_type - ',subscription_type)
         else:
            snstopic = os.environ['servicenowtopic']
            print("Publishing notification to common servicenow topic.")
         sns_client = boto3.client('sns')
         snsTopic = snstopic
         sns_client.publish(
            MessageStructure='json',
            Message=message,
            Subject='AWSMS Offerings Alerts',
            TopicArn=snsTopic)
         print("Published successfully")
    except Exception as e:
      print('Error:publish_message(): ', e)

def get_priority():
   try:
      config=Config(retries=dict(max_attempts=10,mode='standard'))
      dynamodb_resource = boto3.resource('dynamodb', config=config)
      table = dynamodb_resource.Table('AccountFeatureDefinitions')
      response = table.get_item(Key={"Feature":"CommonSNSTopic"})
      incident_priority = response['Item']['FeatureParams']['pIncidentPriority']['Default']
      return incident_priority
   except Exception as e:
      print("Error-getpriority-",e)

def handler(event, context):
   try:
      print('Received Event:',event)
      json_message_for_snow = prepare_json_message_for_snow(event)
      json_message_for_email = prepare_json_message_for_email(event)
      
      publish_message(json_message_for_email, 'email')
      if(json_message_for_snow):
         publish_message(json_message_for_snow['formatted_snow_message'], 'https')
      else:
         print('Event is Not an Alarm, so skipping sending to SNOW')
   except Exception as e:
      print('Error Occurred: ',e)
