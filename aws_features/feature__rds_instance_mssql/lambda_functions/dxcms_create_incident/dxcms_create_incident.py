import json
import boto3
import os
from uuid import uuid4
import datetime
from botocore.config import Config

def get_db_items(client,item_name):
    try:
        response = client.get_item(Key={"Feature":item_name})
        return response['Item']
    except Exception as e:
        print("Error-get_db_items()",e)

def sns_publish(client,message,sns_arn,subject=None):
    try:
        if subject:
            response = client.publish(TopicArn=sns_arn,Message=message,Subject=subject)
        else:
            response = client.publish(TopicArn=sns_arn,Message=message)
    except Exception as e:
        print("Error-sns_publish()",e)


def lambda_handler(event, context):
    try:
        print("Received Event-{}".format(event))
        feature_name=os.environ["FEATURE_NAME"]
        
        config=Config(retries=dict(max_attempts=10,mode='standard'))
        primary_region=os.environ["PRIMARY_REGION"]
        primary_sns_client=boto3.client('sns',region_name=primary_region,config=config)
        
        if "lambda" in event:
            msg={}
            sns_topic=os.environ["SERVICENOW_TOPIC"]
            msg['message']=event["lambda"]
            msg["endpoint_url"]=event["endpoint_url"]
            snow_title=event["snow_title"]
            message={
           "EventList":[
             {
               "eventsourcesendingserver": "Feature-{}".format(feature_name),
               "eventsourceexternalid": str(uuid4()),
               "title": snow_title,
               "longDescription": msg,
               "application": "Relational Database Service",
               "eventsourcecreatedtime": str(datetime.datetime.now()),
               "PriorityData": {
                "Priority": "1"
              }
              }    
              ] 
              }
            snsJson = json.dumps(message)
            ApiEventMsg = snsJson
            
            sns_publish(primary_sns_client,ApiEventMsg,sns_topic)
            print("Published the message to topic: {} successfully".format(sns_topic))
        
        else:
            subject=event['Records'][0]['Sns']['Subject']
            message=event['Records'][0]['Sns']['Message']
            
            
            table_name="AccountFeatureDefinitions"
            
            primary_dynamodb = boto3.resource('dynamodb',region_name=primary_region)
            table = primary_dynamodb.Table(table_name)
            item=get_db_items(table, feature_name)
            
            
            
            primary_sns_topic=item['RDSParameters']['PriorityIncidentTopic']['Default']
            
            sns_publish(primary_sns_client,message,"arn:aws:sns:"+primary_region+":"+context.invoked_function_arn.split(":")[4]+":"+primary_sns_topic,subject)
            print("Published the message to topic {} successfully".format(primary_sns_topic))
    except Exception as e:
        print("Error-lambda_handler()",e)
        
