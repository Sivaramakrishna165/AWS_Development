'''
boto_helper class constains all the methods related to 
boto3 operations
'''
import boto3
import time
import yaml
import json
from botocore.config import Config

class boto_helper():
    def __init__(self, pipeline, region, cross_acc_role):
        self.config = Config(retries=dict(max_attempts=10,mode='standard'))        
        self.tags = [{'Key':'Owner','Value':'DXC'}, 
                        {'Key':'Application','Value':'AWS Managed Services'}, 
                        {'Key':'CICD-Pipeline','Value':pipeline}, 
                    ]
        if(cross_acc_role == ''):
            self.cf_client = boto3.client('cloudformation', config=self.config, region_name = region)
        else:
            stsclient = boto3.client('sts', config=self.config)
            awsaccount = stsclient.assume_role(RoleArn=cross_acc_role,  RoleSessionName='DXC-AWSMS-CICD-CrossAccountRole')
            ACCESS_KEY = awsaccount['Credentials']['AccessKeyId']
            SECRET_KEY = awsaccount['Credentials']['SecretAccessKey']
            SESSION_TOKEN = awsaccount['Credentials']['SessionToken']
            
            self.cf_client = boto3.client('cloudformation',region_name = region, aws_access_key_id=ACCESS_KEY, aws_secret_access_key=SECRET_KEY, aws_session_token=SESSION_TOKEN, config=self.config)
        
        self.ddb = boto3.resource('dynamodb', config=self.config)
        self.event_rule = boto3.client('events', config=self.config)
        self.ssm_client = boto3.client('ssm', config=self.config)
    
    def get_ssm_param_value(self, param):
        try:
            response = self.ssm_client.get_parameter(Name=param)
            return response['Parameter']['Value']
        except:
            raise
        
    def describe_stacks(self):
        try:
            args = {}
            stacks_lst =[]
            while True:
                response = self.cf_client.describe_stacks(**args)
                if('Stacks' in response):
                    for stack in response['Stacks']:
                        if 'Tags' in stack and all([tag in stack['Tags'] for tag in self.tags]):
                            json_obj = {}
                            json_obj['StackName'] = stack['StackName']
                            json_obj['Status'] = stack['StackStatus']
                            if('Description' in stack):
                                json_obj['StackDescription'] = stack['Description']
                            
                            stacks_lst.append(json_obj)
                if('NextToken' in response):
                    args['NextToken'] = response['NextToken']
                else:
                    break
            return stacks_lst
        except Exception as e:
            error = 'Stack with id {} does not exist'.format(stack)
            if error in str(e):
                print('Error: describe_stacks() - ',e)
                return None
            raise e
            
    def add_items(self, tbl_name, obj_json):
        try:
            table = self.ddb.Table(tbl_name)
            table.put_item(Item=obj_json)
        except boto3.exceptions.botocore.client.ClientError as e:
            print("Error adding item: {}  - {}".format(obj_json, str(e)))
            raise
    
    def describe_dynamo_items(self, tbl_name):
        try:
            table = self.ddb.Table(tbl_name)
            response = table.scan()
            
            result = []
            for item in response['Items']:
                obj = {}
                obj['StackName'] = item['StackName']
                obj['StackDescription'] = item['StackDescription']
                obj['Status'] = item['Status']
                obj['Comments'] = item['Comments']
                result.append(obj)
            return result
        except Exception as e:
            raise e
    
    def enable_event_rule(self,event):
        try:
            self.event_rule.enable_rule(Name=event)
        except Exception as e:
            raise e
    
    def disable_event_rule(self,event):
        try:
            self.event_rule.disable_rule(Name=event)
        except Exception as e:
            raise e