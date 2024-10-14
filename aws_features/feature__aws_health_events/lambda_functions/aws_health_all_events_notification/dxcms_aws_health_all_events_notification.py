'''
This lambda function created as part of the story AWSPE-7065.
The lambda will format all the AWS health events and publish the same to the SNS topic.
'''

import json
import boto3
import os
from botocore.config import Config

config = Config(retries=dict(max_attempts=10,mode='standard'))
sns_client= boto3.client("sns",config=config)

topic_arn = os.environ['notification_topic']

def lambda_handler(event, context):
    
    try:
        print('Event Received -->', event)
        text = 'Please find the AWS Health Notification below:\n\n'
        text+=json.dumps(event, indent=4)
        
        response = sns_client.publish(
            TopicArn=topic_arn,
            Message=text,
            Subject= "-".join(['AWS Health Notification',event['account'], event['region']])
        )
        print('message published successfully')    
    except Exception as e:
        print('Error-->', str(e))