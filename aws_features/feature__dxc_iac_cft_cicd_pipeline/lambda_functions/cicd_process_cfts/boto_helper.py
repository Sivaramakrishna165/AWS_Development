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
        # Constant Variables
        self.stack_status = {'CREATE_COMPLETE':'Creation COMPLETE, stack - ',
                            'UPDATE_COMPLETE':'Update COMPLETE, stack - ',
                            'CREATE_FAILED':'Create FAILED stack, - ',
                            'UPDATE_ROLLBACK_COMPLETE':'Update FAILED, Rollback complete stack, - ',
                            'ROLLBACK_COMPLETE':'Create FAILED, Rollback complete. stack - '}
        
        self.s3_client = boto3.client('s3', config=self.config)
        self.ddb = boto3.resource('dynamodb', config=self.config)
        self.event_rule = boto3.client('events', config=self.config)
            
        if(cross_acc_role == ''):
            self.cf_client = boto3.client('cloudformation', config=self.config, region_name = region)
        else:
            stsclient = boto3.client('sts', config=self.config)
            awsaccount = stsclient.assume_role(RoleArn=cross_acc_role,  RoleSessionName='DXC-AWSMS-CICD-CrossAccountRole')
            ACCESS_KEY = awsaccount['Credentials']['AccessKeyId']
            SECRET_KEY = awsaccount['Credentials']['SecretAccessKey']
            SESSION_TOKEN = awsaccount['Credentials']['SessionToken']
            
            self.cf_client = boto3.client('cloudformation',region_name = region, aws_access_key_id=ACCESS_KEY, aws_secret_access_key=SECRET_KEY, aws_session_token=SESSION_TOKEN, config=self.config)
        
    def get_s3_object(self,  bucket, key):
        try:
            template = None
            response = self.s3_client.get_object(Bucket=bucket, Key=key)
            if 'Body' in response:
                file = response['Body'].read()
                if ('.json' in key):
                    template = json.loads(file)
                else:
                    template = yaml.load(file, Loader=yaml.BaseLoader)
            
            return template
        except Exception as e:
            print('Error get_s3_object() - ', e)
            
    # Create a stack, provide stack params, boto_session, region
    def create_stack(self, stack_params):
        try:
            stack_params['DisableRollback'] = True
            stack_params['Tags'] = self.tags
            stack_params['Capabilities']=['CAPABILITY_IAM','CAPABILITY_NAMED_IAM']
            
            self.cf_client.create_stack(**stack_params)
            
        except Exception as e:
            print('create_stack() ',e)
            raise
        
    #  Checks if stack exists
    def bln_check_stack_exists(self, stack):
        try:
            status = self.cf_client.describe_stacks(StackName=stack)['Stacks'][0]['StackStatus']
            return status
        except Exception as e:
            error = 'Stack with id {} does not exist'.format(stack)
            if error in str(e):
                print('Error: check_stack_status() - ',e)
                return None
            raise e
            
    def add_items(self, tbl_name, obj_json):
        try:
            table = self.ddb.Table(tbl_name)
            table.put_item(Item=obj_json)
        except boto3.exceptions.botocore.client.ClientError as e:
            print("Error adding item: {}  - {}".format(obj_json, str(e)))
            raise
    
    def create_stack_change_set(self, stack_info):
        try:
            stack_info['UsePreviousTemplate']=False
            stack_info['Tags'] = self.tags
            stack_info['Capabilities']=['CAPABILITY_IAM','CAPABILITY_NAMED_IAM']
            
            response = self.cf_client.create_change_set(**stack_info)
            print('Create_Change_Set', response)
            return response
        except Exception as e:
            print('Error create_stack_change_set', e)
            raise
    
    def describe_change_set(self, stack_info):
        try:
            while True:
                response = self.cf_client.describe_change_set(
                    StackName=stack_info['StackName'],
                    ChangeSetName = stack_info['ChangeSetName'])

                if (response['Status'] not in ['CREATE_IN_PROGRESS', 'CREATE_PENDING']): 
                    return response['Changes'] if 'Changes' in response else []
                time.sleep(1)           
                
            return []            
        except Exception as e:
            print('Error describe_change_set', e)
            raise  
    
    def execute_change_set(self, change_set, stack_name):
        try:
            response = self.cf_client.execute_change_set(
                    ChangeSetName=change_set,
                    StackName=stack_name,
                    DisableRollback=False
                )
        except Exception as e:
            print('Error execute_change_set() ',e)
            raise
        
    def update_stack(self, stack_params):
        try:
            stack_params['Tags'] = self.tags
            stack_params['Capabilities']=['CAPABILITY_IAM','CAPABILITY_NAMED_IAM']
            self.cf_client.update_stack(**stack_params)

            return True
        except Exception as e:
            if('No updates are to be performed' in str(e)):
                return False
            else:    
                print('update_stack() ',e)
                raise
    
    def enable_event_rule(self,event):
        try:
            self.event_rule.enable_rule(Name=event)
        except Exception as e:
            raise e
        