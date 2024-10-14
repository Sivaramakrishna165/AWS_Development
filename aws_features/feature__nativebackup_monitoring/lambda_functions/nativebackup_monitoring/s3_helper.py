'''
Boto Helper class contain all the supported aws api operations
'''
import boto3
import json
from botocore.config import Config
from boto3.dynamodb.conditions import Key

class s3_helper():

    def __init__(self):
        self.config = Config(retries=dict(max_attempts=10,mode='standard'))
        self.ddb = boto3.resource('dynamodb', config=self.config)
        self.sns_client = boto3.client('sns', config = self.config)
        self.feature_name = 'NativebackupS3'

    def get_db_object(self,afd_table,val_to_fetch,feature_name):
        try:
            table = self.ddb.Table(afd_table)
            response = table.query(KeyConditionExpression=Key('Feature').eq(feature_name))
            print('S3 Response-', response)

            for item in response['Items']:
                fetched_object = item['FeatureParams'][val_to_fetch]['Default']
                print('priority:',fetched_object)

            return fetched_object
        except Exception as e:
            print('error in get_db_object():',e)
            raise

    def publish_to_common_snow_topic(self,sns_topic,api_message):
        try:
            print("############ Publishing message to SNS topic has been started ############")
            self.sns_client.publish(TopicArn=sns_topic, Message=api_message)
            print("############ Publishing message to SNS topic has been completed ############")
        except Exception as e:
            print("Error-", e)
            raise

    def create_json_payload_and_sns_publish(self,event,sns_topic,afd_table,val_to_fetch):
        try:
            print("########## Json payload creation started ##########")
            event_id=event['id']
            event_detail=event['detail']
            event_detail_type=event['detail-type']
            event_account = event['account']
            event_region = event['region']
            event_time = event['time']
            resource_arn=event['detail']['resourceArn']
            service_name=resource_arn.split(":")[2]
            job_state=event['detail']['state']
            resource_name=resource_arn.split(":")[5]
    
            priority={'1': 'critical', '2': 'major', '3': 'minor', '4':'warning', '5':'ok'}
            short_description='Native Backup ' + job_state + ' for ' + service_name + ' bucket ' + resource_name
            get_incident_impact=self.get_db_object(afd_table,val_to_fetch,self.feature_name)
            
            incidentEventSourceSendingServer=service_name
            incidentEventSourceExternalid=event_id
            incidentSeverity=priority[get_incident_impact]
            incidentTitle=short_description
            incidentLongDescription=event_detail
            incidentCategory='AWS Backup Monitoring'
            incidentApplication=event_detail_type + ' EventAccount: ' + event_account + ' EventRegion:' +  event_region + ' Status: ' + job_state
            incidentCreateDt=event_time
            findingIncidentCategory='Integration'
            findingIncidentSubcategory='Data'
            findingIncidentImpact=get_incident_impact
            
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
                "PriorityData": {
                    "Priority": findingIncidentImpact
                }
            }    
            ]
            }
            
            api_message=json.dumps(eventMsg)
            print('API message-', api_message)
            print("########## Json payload creation completed ##########")
            
            sns_publish = self.publish_to_common_snow_topic(sns_topic,api_message)
        
        except Exception as e:
            print("Error - ", e)
            raise