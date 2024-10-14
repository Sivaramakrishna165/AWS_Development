'''
Boto Helper class contain all the supported aws api operations
'''

import boto3
from botocore.config import Config
import time
import json

class boto_helper():
    
    def __init__(self):
        self.config = Config(retries=dict(max_attempts=10,mode='standard'))
        self.state_client = boto3.client('stepfunctions', config = self.config)
        self.ec2_client = boto3.client('ec2', config = self.config)
        self.ssm_client = boto3.client('ssm', config = self.config)
    
    #To execute the ssm command    
    def execute_ssm_send_command(self,instance_id, document_name, command):
        
        try:
            ssm_response = self.ssm_client.send_command(
                InstanceIds=[instance_id],
                DocumentName=document_name,
                Parameters={'commands':command},
                )
                
            commandid=ssm_response['Command']['CommandId']
            time.sleep(5)
            
            return commandid
        
        except Exception as e:
            print('Error -', str(e))
            raise
    
    #To get the status of the command    
    def get_invocation_status(self, instance_id, commandid):
        
        try:
            output = self.ssm_client.get_command_invocation(
                CommandId=commandid,
                InstanceId=instance_id
                )
            status = output['Status']
            
            return status
        
        except Exception as e:
            print('Error - ', str(e))
            raise
            
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
    
    # Send task success to step function    
    def send_task_success(self,taskToken,payload_json):
        
        try:
            print("send_task_success Execution started")
            response = self.state_client.send_task_success(
                taskToken=taskToken,
                output = json.dumps(payload_json)
            )
            print('Task SUCCESS token sent - ',response)

        except Exception as e:
            print('Error send_task_success()-',e)
            raise    
            
    #To Send task failure to step function
    def send_task_failure(self,taskToken, error, cause):
        
        try:
            print("send_task_failure Execution started")
            response = self.state_client.send_task_failure(
                taskToken=taskToken,
                error = error,
                cause = cause
            )
            print('Task FAILURE token sent - ',response)

        except Exception as e:
            print('Error send_task_failure()-',e)
            raise
    
    #To perform operations upon success        
    def handle_success(self, taskToken, payload_json):
        
        try:
            self.send_task_success(taskToken, payload_json)
            
        except Exception as e:
            print("Error-", e)
            raise    
    
    #To perform operations upon failure        
    def handle_failure(self, taskToken, error, instance_id):
        
        try:
            self.update_tag(instance_id, 'edr', 'Failed')
            self.send_task_failure(taskToken, json.dumps(error), error['Cause'])
            
        except Exception as e:
            print("Error-", e)
            raise