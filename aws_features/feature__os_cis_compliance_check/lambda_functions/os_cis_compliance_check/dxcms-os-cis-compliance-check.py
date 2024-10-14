# This Lambda functions is triggered 
# only when objects are uploaded to s3 bucket dxc.customer.cis.compliance-<account>-<region>
# test-event: {'Records': [{'s3': {'object': {'key': '08-23-2022/compliance/i-014c20bdc9949bc1f_08232022_091020.tar.gz', 'eTag': 'a35c7a5f32f71c44f2799173f90b32c3'}}}]}
# For non-compliance Instances, a service now incident is created using snowurl

import boto3
import time
import os
import json
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))
ec2_client = boto3.client('ec2',config = config)
cw_client = boto3.client('logs',config = config)
sns_client = boto3.client('sns',config = config)
sts_client = boto3.client("sts",config = config)

log_group_name = os.environ['log_group_name']
log_stream_compliance = os.environ['log_stream_compliance']
log_stream_non_compliance = os.environ['log_stream_non_compliance']


def format_message(event, instance_id, result):
    try:
        formatMessage_response = {'formatted_snow_message': None, 'reason': None}
        account = sts_client.get_caller_identity()['Account']
        eventMsg = {
          "Trigger": {
            "MetricName": 'DXC AWSMS OS CIS non-Compliance Instance',
            "Dimensions": [
              {
                "name": "InstanceId",
                "value": instance_id
              }
            ]
          },
          "AlarmName": "DXC-AWSMS-OS-CIS-non-Compliance",
          "NewStateReason": result,
          "AWSAccountId": account,
          "NewStateValue": "ALARM",
          "correlation_id": event['Records'][0]['s3']['object']['eTag'],
          "InstanceId": instance_id
        }
        eventMsg['eventData'] = event
        eventMsg['err'] = None

        message = 'Sending a DXC AWSMS OS CIS non-Compliance instance' 
        snsJson = {}
        snsJson['default'] = message
        snsJson['https'] = json.dumps(eventMsg)
        snsJson['email'] = json.dumps(eventMsg)
        snsJsonMsg = json.dumps(snsJson)

        formatMessage_response['formatted_snow_message'] = snsJsonMsg 
        formatMessage_response['reason'] = 'SUCCESS'

        return formatMessage_response
    except Exception as e:
        print(str(e))


def sns_publish(snow_message):
  try:  
    snsTopic = os.environ['snstopic']
    sns_client.publish(
        MessageStructure='json',
        Message=snow_message,
        Subject='DXC AWSMS OS CIS non-Compliance Instance',
        TopicArn=snsTopic
    )
    print('Notification published successfully')
  except Exception as e:
    print('Error:send_to_ServiceNow()-', e)

def log_event(instance_id, result, log_stream):
  try:
    response_cws = cw_client.describe_log_streams(logGroupName=log_group_name, logStreamNamePrefix=log_stream)                 
                  
    if 'uploadSequenceToken' in response_cws['logStreams'][0]:
      
      cw_client.put_log_events(
        logGroupName = log_group_name,
        logStreamName = log_stream,
        sequenceToken = response_cws['logStreams'][0]['uploadSequenceToken'],
        logEvents = [{
          'timestamp' : round(time.time() * 1000),
          'message' : '{} - {}'.format(instance_id, result)
        }])
    else:
      cw_client.put_log_events(
        logGroupName = log_group_name,
        logStreamName = log_stream,
        logEvents = [{
          'timestamp' : round(time.time() * 1000),
          'message' : '{} - {}'.format(instance_id, result)
        }])
          
      
  except:
    pass

# Events triggered on File uploaded to S3 bucket
def main(event,context):
  try:
    print(event)
    ObjectName = event['Records'][0]['s3']['object']['key']
    cistype = ObjectName.split("/")[1]  # Expected value here is compliance/non-compliance
    instance_id = ObjectName.split("/")[-1].split("_")[0]
    if(cistype.lower() == 'compliance'):
      ec2_client.create_tags(Resources=[instance_id], Tags=[{'Key':'OS-CIS-Compliance', 'Value':'True'}])
      result = 'Complaince. CoreCM Installed.'
      log_event(instance_id, result, log_stream_compliance)

    elif(cistype.lower() == 'non-compliance'):
      ec2_client.create_tags(Resources=[instance_id], Tags=[{'Key':'OS-CIS-Compliance', 'Value':'False'}])
      result = 'non-Complaince. CoreCM NOT Installed.'
      log_event(instance_id, result, log_stream_non_compliance)
      # Publish event details for SNS Topic(snowurl, email)
      formatted_json = format_message(event, instance_id, result)            
      sns_publish(formatted_json['formatted_snow_message'])     
    
    return "{} - {}".format(instance_id, result)
  except Exception as e:
    print("Error ", e)