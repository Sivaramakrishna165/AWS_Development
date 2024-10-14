'''
Boto Helper class contain all the supported aws api operations
'''

import boto3
from botocore.config import Config
from datetime import datetime

class boto_helper():
    
    def __init__(self):
        self.config = Config(retries=dict(max_attempts=10,mode='standard'))
        self.ddb = boto3.resource('dynamodb', config=self.config)
        self.ddb_client = boto3.client('dynamodb', config=self.config)
        self.state_client = boto3.client('stepfunctions', config = self.config)
        self.log_client = boto3.client('logs', config = self.config)
    
    #To check the item existence in the table
    def check_db_entry_exists(self, tbl_name, item_name, item_value):
        result = False
    
        try:
            table = self.ddb.Table(tbl_name)
            get_item_response = table.get_item(Key={item_name: item_value})
            if get_item_response['Item'][item_name] == item_value:
                print('Item %s found' % item_value)
                return True
            else:
                print('Item %s not found' % item_value)
                return False
        except KeyError as e:
            print(str(e) + "KeyError exception in check_db_entry_exists")
            return False        

    #To add the items to the Dynamodb MM tables.    
    def add_items(self,tbl_name, ddb_json):
        
        try:
            
            table = self.ddb.Table(tbl_name)
            print(ddb_json)
            
            table.put_item(Item=ddb_json)
            print("Item added to the table-",tbl_name)
            
        except Exception as e:
            print("Error adding item: {}  - {}".format(ddb_json, str(e)))
            raise
    
    def create_ddb_table_param_set_item(self):
        try:
        
            ddb_param_set_json = {
                'ParameterSetName': 'Default',
                'Backup':'true',
                'Encryption':'true',
                'KMS':'Default',
                'Alarm':'true'
            }
            
            print("created the parameter set table json-", ddb_param_set_json)
            
            return ddb_param_set_json
            
        except Exception as e:
            raise
    
    #To construct alarm table items in json format.
    def create_ddb_table_alarm_item(self,event_results_json,default_ddb_table_alarm):
        default_alarms = default_ddb_table_alarm
        
        try:
            
            default_ddb_alarm_json = {
                'TableName':event_results_json['tablename'],
                'Alarms': default_alarms
            }
            
            print("created the alarm table json-", default_ddb_alarm_json)
            
            return default_ddb_alarm_json
            
        except Exception as e:
            raise
    
    #To construct report table items in json format.
    def create_ddb_table_report_item(self,event_results_json):
        currentDT = datetime.now()
        date_time = currentDT.strftime('%m-%d-%Y_%H%M%S')
        
        try:
            
            ddb_rep_json = {
                'TableName':event_results_json['tablename'],
                'ParameterSetName' : event_results_json['dxc_dynamodb_parameter_set'],
                'CreationTime': date_time,
                'ModifyTime': '',
                'StateName': '',
                'StateSuccessFail': '',
                'StateDetail': ''
            }
            
            print("created the report table json-", ddb_rep_json)
            
            return ddb_rep_json
            
        except Exception as e:
            raise

    #To invoke the step function    
    def call_state_machine(self,state_machine_input, state_fun_arn):
        
        try:
            
            state_start_response = self.state_client.start_execution(
            stateMachineArn=state_fun_arn,
            input=state_machine_input
            )
            
            print("state_start_response is ", state_start_response)
            
        except Exception as e:
            print(str(e) + " exception in call_state_machine")

    #To update the tag on the user created table.        
    def update_tag(self,TabArn,key,value):
        
        try:
            
            update_tag_response = self.ddb_client.tag_resource(
                ResourceArn=TabArn,
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
            
    #To construct report table items in json format updon processor failure.
    def create_ddb_table_report_item_failure(self,event_results_json,statename,status):
        currentDT = datetime.now()
        date_time = currentDT.strftime('%m-%d-%Y_%H%M%S')
        
        try:
            
            ddb_rep_json = {
                'TableName':event_results_json['tablename'],
                'ParameterSetName' : event_results_json['dxc_dynamodb_parameter_set'],
                'CreationTime': date_time,
                'ModifyTime': date_time,
                'StateName': statename,
                'StateSuccessFail': status,
                'StateDetail': event_results_json['tags_valid']
            }
            
            print("created the report table json-", ddb_rep_json)
            
            return ddb_rep_json
            
        except Exception as e:
            raise

    #To create and load the logs into specific log stream
    def create_log_stream(self, log_group, log_stream, message):
        try:
            response = self.log_client.create_log_stream(
            logGroupName=log_group,
            logStreamName=log_stream
            )
            print("{} log stream created successfully".format(log_stream))
            
            response = self.log_client.put_log_events(
                logGroupName=log_group,
                logStreamName=log_stream,
                logEvents=[
                    {
                        'timestamp': int(datetime.utcnow().timestamp() * 1000),
                        'message': message
                    },
                ]
            )
         
        except Exception as e:
            print("Error while creating/updating the log stream -", e)
            raise    
    
    #To load the logs into log stream
    def put_log(self, log_group, log_stream, message):
        try:

            response = self.log_client.put_log_events(
                logGroupName=log_group,
                logStreamName=log_stream,
                logEvents=[
                    {
                        'timestamp': int(datetime.utcnow().timestamp() * 1000),
                        'message': message
                    },
                ]
            )
        except self.log_client.exceptions.ResourceNotFoundException:
            print("Creating logStreamName ", log_stream)
            self.create_log_stream(log_group, log_stream, message)
        except Exception as e:
            print("Error occured in put_log():",e)
            raise