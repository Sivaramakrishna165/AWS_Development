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
        self.log_client = boto3.client('logs', config = self.config)

    #To get the backup tag value from the param set table.
    def get_param_set_backup_item(self,parameterSetName,ddb_param_set_table):
        try:
            table = self.ddb.Table(ddb_param_set_table)
            
            param_set_backup_response = table.get_item(Key={
                            'ParameterSetName': parameterSetName
                        })
                        
            print("param_set_backup_response-", param_set_backup_response)

            table_backup = param_set_backup_response['Item']['Backup']
            print("Backup-", table_backup)
            return table_backup
            
        except Exception as e:
            print("Error-", e)
            raise

    #To convert the string value to boolean
    def str_to_bool(self,param_set_backup_check):
        if param_set_backup_check.lower() == 'true':
            return True
        elif param_set_backup_check.lower() == 'false':
            return False
        else:
            raise ValueError
    
    #To Enable/Disable the backup on the Dynamodb tables        
    def update_table_backup(self,tableName,bool_backup):
        try:
            response = self.ddb_client.update_continuous_backups(
                TableName=tableName,
                PointInTimeRecoverySpecification={
                    'PointInTimeRecoveryEnabled': bool_backup
                }
            )
            print("Backup Response-", response)
            return 'success'
            
        except Exception as e:
            print("Error-", e)
            return 'fail'
            
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
            
    # Send task failure to step function
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
            print('Error send_task_success()-',e)
            raise

    #To update tag values on the user created tables        
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

    #To update the report table with the current status        
    def update_report_table(self,ddb_rep_table,tableName,status,statedetail,stateName, parameterSetName):
        try:
            table = self.ddb.Table(ddb_rep_table)
            currentDT = datetime.now()
            date_time = currentDT.strftime('%m-%d-%Y_%H%M%S')
            
            table.update_item(
                Key={
                    'TableName': tableName
                },
                UpdateExpression='SET ModifyTime=:time, StateName=:state, StateSuccessFail=:status, StateDetail=:detail, ParameterSetName=:parametersetname',
                ExpressionAttributeValues={
                    ':time': date_time,
                    ':state': stateName,
                    ':status': status,
                    ':detail': statedetail,
                    ':parametersetname': parameterSetName
                }
            )
        except Exception as e:
            print("Error in update_report_table", e)
            raise
    
    #To update report table and send success token - success         
    def handle_success(self, ddb_rep_table, tableName, stateName, message, taskToken, payload_json, parameterSetName):
        try:
            self.update_report_table(ddb_rep_table, tableName, 'SUCCESS', message, stateName, parameterSetName)
            self.send_task_success(taskToken, payload_json)
        except Exception as e:
            print("Error-", e)
            raise
    
    #To update the tag, report table and send failure token - Failure
    def handle_failure(self, tableArn, ddb_rep_table, tableName, stateName, taskToken, error, parameterSetName):
        try:
            self.update_tag(tableArn, 'dxc_dynamodb_make_manage', 'Fail')
            self.update_report_table(ddb_rep_table, tableName, 'FAIL', error['Error'], stateName, parameterSetName)
            self.send_task_failure(taskToken, json.dumps(error), error['Cause'])
        except Exception as e:
            print("Error-", e)
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