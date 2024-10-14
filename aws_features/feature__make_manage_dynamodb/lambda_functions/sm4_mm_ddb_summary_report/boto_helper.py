'''
Boto Helper class contain all the supported aws api operations required to perform backup operation
'''
import boto3
from botocore.config import Config
import json
from datetime import datetime

class boto_helper():

    def __init__(self):
        self.config = Config(retries=dict(max_attempts=10,mode='standard'))
        self.ddb = boto3.resource('dynamodb', config=self.config)
        self.ddb_client = boto3.client('dynamodb', config=self.config)
        self.state_client = boto3.client('stepfunctions', config = self.config)
        self.s3_client = boto3.client('s3', config=self.config)
        self.s3_resource = boto3.resource('s3', config=self.config) 
        self.ssm_client = boto3.client("ssm", config=self.config)
        self.log_client = boto3.client('logs', config = self.config)
    
    #To update the status in the dynamodb table tag
    def update_tag(self,TabArn,key,status):
        if status=="SUCCESS":
            value='Managed'
        else:
            value='Fail'
        
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

    #To update the report table with the current status        
    def update_report_table(self,ddb_rep_table,tableName,status,statedetail):
        try:
            table = self.ddb.Table(ddb_rep_table)
            currentDT = datetime.now()
            date_time = currentDT.strftime('%m-%d-%Y_%H%M%S')
            
            table.update_item(
                Key={
                    'TableName': tableName
                },
                UpdateExpression='SET ModifyTime=:time, StateSuccessFail=:status, StateDetail=:statedetail',
                ExpressionAttributeValues={
                    ':time': date_time,
                    ':status': status,
                    ':statedetail':statedetail
                }
            )
            print("Report table updated successfully")
            
        except Exception as e:
            print("Error in update_report_table", e)
            raise
        
    def get_table_report_data(self,ddb_rep_table,TableName):
        try:
            table = self.ddb.Table(ddb_rep_table)
            response = table.get_item(Key={
                    'TableName': TableName
                })
            print("successfully retrieved the data from report table-")
            table_report_data = response['Item']
            print("Table Report Data-", table_report_data)
            return table_report_data
        
        except Exception as e:
            print("Error in fetching the data from report table", e)
            raise
        
    def get_parameter(self,param_name):
        try:
            response = self.ssm_client.get_parameter(Name = param_name,WithDecryption=True)['Parameter']['Value']
            print("Response-", response)
            return response
        except Exception as e:
            print("Error-",e)
            raise
        
    # Read s3 object
    def read_s3_object(self, bucket, key):
        try:
            data = self.s3_client.get_object(Bucket=bucket, Key=key)
            return data
        except Exception as e:
            print('Error read_s3_object() -',e)
            raise
        
    def upload_file(self,tmpfile,customer_bucket,location):
        try:
            response=self.s3_resource.meta.client.upload_file(tmpfile,customer_bucket,location)
        except Exception as e:
            print("Error -", e)
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