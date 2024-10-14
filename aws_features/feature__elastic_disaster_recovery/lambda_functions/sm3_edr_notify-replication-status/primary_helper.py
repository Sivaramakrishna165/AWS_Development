'''
Boto Helper class contain all the supported aws api operations
'''

import boto3
from botocore.config import Config
import json

class primary_boto_helper():
    
    def __init__(self):
        self.config = Config(retries=dict(max_attempts=10,mode='standard'))
        self.sns_client = boto3.client('sns', config = self.config)
        self.ec2_client = boto3.client('ec2', config = self.config)
        
    #To update the tag value on the instance        
    def update_tag(self, InstId, key, value):
        
        try:
            update_tag_response = self.ec2_client.create_tags(
                Resources=[
                    InstId,
                ],
                Tags=[
                    {
                        'Key': key,
                        'Value': value
                    },
                ]
            )
            print("update_tag_response is ", update_tag_response)
        except Exception as e:
            print("Error in update_tag", e)
            raise         
        
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