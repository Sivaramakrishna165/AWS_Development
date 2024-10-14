import boto3
from time import sleep
import os
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))

cloud_ops_email = os.environ['CloudOps_Email_Parameter']
topic_arn = os.environ['SNS_Topic_Arn']

sns = boto3.client('sns', config=config)
ssm = boto3.client('ssm', config=config)

def get_ssm_paramter(s3_bucket):
    try:
        value = ""
        response = ssm.get_parameter(
            Name=s3_bucket
        )
        value = response['Parameter']['Value']
    except Exception as e:
        value = ""
        print("unable to cont ..",e)
    return value

        
def lambda_handler(event, context):
    try:
        sub_arns=[]
        
        end=[]

        emails = get_ssm_paramter(cloud_ops_email)
        endpoints_mails = emails
        endpoints = list(endpoints_mails.split(","))
        print(endpoints)

        response4 = sns.list_subscriptions_by_topic(
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
                response2 = sns.subscribe(
                    TopicArn=topic_arn,
                    Protocol='email',
                    Endpoint=endpoint,
                    ReturnSubscriptionArn=True
                )   
                sub_arns.append(response2['SubscriptionArn'])
        
        
        #accessing one by one subscription
        for sub_arn in sub_arns:
            response3 = sns.get_subscription_attributes(
                SubscriptionArn=sub_arn
            )
            
            #validating the confirm subscription
            while(sns.get_subscription_attributes(SubscriptionArn=sub_arn)['Attributes']['PendingConfirmation']=='true'):
    
                sleep(5)
                

        #Publishing the payload to the sns topic 
        print("msg publishing")
        response4 = sns.publish(
            TopicArn=topic_arn,
            Message=str(event)
        )
        
    except Exception as e:
        print(e)
