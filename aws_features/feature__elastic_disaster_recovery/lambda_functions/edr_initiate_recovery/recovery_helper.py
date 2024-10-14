'''
Boto Helper class contain all the supported aws api operations
'''

import boto3
from botocore.config import Config
from boto3.dynamodb.conditions import Key, Attr
import json

class recovery_boto_helper():
    
    def __init__(self):
        self.config = Config(retries=dict(max_attempts=10,mode='standard'))
        self.ec2_client = boto3.client('ec2', config = self.config)
        self.ddb_resource = boto3.resource('dynamodb', config = self.config)
        self.drs_client = boto3.client('drs', config = self.config)
        self.sns_client = boto3.client('sns', config = self.config)
    
    #To scan the table and get all the instance in the affected region    
    def get_instance_info(self, table_name, primary_region):
        
        try:
            instance_list = []
            table = self.ddb_resource.Table(table_name)
            response = table.scan(
                FilterExpression=Key('PrimaryRegion').eq(primary_region),
                ProjectionExpression='InstanceId'
            )

            print(response)
            for instance in response['Items']:
                instance_list.append(instance['InstanceId'])
            return instance_list
        
        except Exception as e:
            print('ERROR -',str(e))
            raise e
     
    #To get the instance's source server id from dynamodb table       
    def get_db_item(self, instance_id, instance_info_table):
        
        try:
            table = self.ddb_resource.Table(instance_info_table)
            response = table.get_item(
                Key={
                    'InstanceId' : instance_id
                },
                ProjectionExpression='SourceServerId',
                )
            source_server_id = response['Item']['SourceServerId']
            return source_server_id
        
        except Exception as e:
            print('ERROR -',str(e))
            
    #To initiate recovery for the affected instance
    def initiate_recovery(self, source_server_id):
        
        try:
            response = self.drs_client.start_recovery(
                sourceServers=[
                    {
                    'sourceServerID': source_server_id
                    }
                    ]
                )
            print('Initiate Recovery Response -',response)
            return response
        
        except Exception as e:
            print('ERROR -',str(e))
            
    
    #To notify the recovery status through email
    def publish_msg(self,topic,text,msg,subject):
        try:
            text+=json.dumps(msg,indent=4)
            sns_params = {
                        'Message': text,
                        'Subject': subject,
                        'TopicArn': topic
                            }
            self.sns_client.publish(**sns_params)
            print("Report Published SUCCESSFULLY to ",topic)
        except Exception as e:
            print("Error-publish_msg",e)