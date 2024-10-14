from urllib import response
import boto3
import json
from botocore.config import Config

class boto_helper():

    def __init__(self, region='us-east-1'):
        config = Config(retries=dict(max_attempts=10,mode='standard'))
        self.orgs_client = boto3.client('organizations', config=config)
        self.sns_client = boto3.client('sns')
    
    def get_db_item(self, tbl_name, key, value ):
        try:
            response = self.ddb_client.get_item(TableName=tbl_name, Key={key: {"S": value}})
            return response
        except Exception as e:
            print('Error get_db_item()',e)
            raise
    
    def accept_handshake(self, handshakeid):
        try:
            response = self.orgs_client.accept_handshake(HandshakeId=handshakeid)
            print(response)
            return response
        except Exception as e:
            print('Error accept_handshake()',e)
            return str(e)
    
    def decline_handshake(self, handshakeid):
        try:
            response = self.orgs_client.decline_handshake(HandshakeId=handshakeid)
            print(response)
            return response
        except Exception as e:
            print('Error decline_handshake()',e)
            return str(e)
    
    def sns_publish(self, topic_arn, message, subject):
        try:
            
            msg = """
            ------------------------------------------------------------------------------------
            AWS Organization Invitation:
            ------------------------------------------------------------------------------------
            
            {msg}


            """.format(msg=message)
            self.sns_client.publish(
                TopicArn=topic_arn,
                Message=json.dumps(
                    {'default': msg}),
                MessageStructure='json',
                Subject=subject
            )
            print('Published message successfully to Topic ',topic_arn)
        except Exception as e:
            print('Error sns_publish()',e)
            raise
    