"""
    Sends an SNS notification with error details

    This Lambda is a part of Selfheal Lambda Anomaly Detection.
    In dxcms_sh_lad_sfn_diagnosis state machine(NotifyForLambdaFunctionFailure),
    gets executed after any state which catches an error.

    Example Input event of the lambda function is:
        {"Payload":{
            "ErrorMessageFrom": "<function_name> Function",
            "Execution": "<execution_id>",
            "StateMachine": "dxcms_sh_lad_sfn_diagnosis",
            "Cause": "<detailed_error_cause>",
            "Error": "<error>"
            }
        }

    In Diagnosis state machine,
    On successful check, ends the state machine
"""

import json
import boto3
from time import sleep
import os
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))

client1 = boto3.client('sns', config=config)
ssm = boto3.client('ssm', config=config)

#Declaring the environment variable for parameter ans sns topic
cloudops_email_id = os.environ['CloudOps_Email_ID']
topic_arn = os.environ['SNS_Topic_Arn']
        
def lambda_handler(event, context):
    try:
        sub_arns=[]
        end=[]
        endpoints = cloudops_email_id.split(',')
        #List out the subsciption
        response4 = client1.list_subscriptions_by_topic(
            TopicArn=topic_arn
        )
        #filtering the subscriptions based on codition
        for index in response4['Subscriptions']:
            if(index['SubscriptionArn']!='PendingConfirmation'):
                end.append(index ['Endpoint'])

        #Accessing one by one endpoint performimg some evalution         
        for endpoint in endpoints: 
            if endpoint in end:
                pass
                # print("exist",endpoint)
            else:
                #creating the subscriptions
                response2 = client1.subscribe(
                    TopicArn=topic_arn,
                    Protocol='email',
                    Endpoint=endpoint,
                    ReturnSubscriptionArn=True
                )   
                sub_arns.append(response2['SubscriptionArn'])
                
        #accessing one by one subscription
        for sub_arn in sub_arns:
            response3 = client1.get_subscription_attributes(
                SubscriptionArn=sub_arn
            )
            freq = 2
            while((client1.get_subscription_attributes(SubscriptionArn=sub_arn)['Attributes']['PendingConfirmation']=='true') and (freq > 0)):
                sleep(2)
                freq = freq -1

        #Publishing the payload to the sns topic    
        response4 = client1.publish(
            TopicArn=topic_arn,
            Message=str(event)
        )
    except Exception as e:
        print("Notification not sent - ", e)