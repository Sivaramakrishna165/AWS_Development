'''
Scripts convert the input into string and passes to sns.
Event passed is:
{
    "Cause": "Cause",
    "Execution": "Execution.Id",
    "StateMachine": "StateMachine",
    "ErrorMessageFrom": "<function_name>"
}
'''

import json
import boto3
import traceback
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
        
        # response = ssm.get_parameter(
        #     Name = ssm_parameter_name
        # )
        # ssm_parameter = response['Parameter']
        
        # endpoints = ssm_parameter['Value'].split(',')
        endpoints = cloudops_email_id.split(',')
        print(endpoints)
        
                
        # response1 = client1.create_topic(
        #     Name='Alert'
        # )
        
        # topic_arn=response1['TopicArn']

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
            print(endpoint)
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
                freq = freq - 1
                

        #Publishing the payload to the sns topic 
        print("msg publishing")
        response4 = client1.publish(
            TopicArn=topic_arn,
            Message=str(event)
        )

    except Exception as e:
        print("Error lambda_handler() - ",e)    
