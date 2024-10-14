"""
Sends an SNS notification with error details

This Lambda is a part of Selfheal EC2 NativeBackupFailure

In all step function, this lambda gets triggered if any of the previous steps catches
an error

Example Input event of the lambda function is:
    {"Payload":{
        "ErrorMessageFrom": "<function_name> Function",
        "Execution": "<execution_id>",
        "StateMachine": "dxcms_sh_eca_sfn_diagnosis",
        "Cause": "<detailed_error_cause>",
        "Error": "<error>"
        }
    }
"""

import json
import boto3
import os
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))

sns_client = boto3.client('sns', config=config)

#Declaring the environment variable for parameter ans sns topic
topic_arn = os.environ['SNS_Topic_Arn']
        
def lambda_handler(event, context):
    try:
        #Publishing the payload to the sns topic    
        response4 = sns_client.publish(
            TopicArn=topic_arn,
            Message=str(event)
        )
    except Exception as e:
        print("Notification not sent - ", e)