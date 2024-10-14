'''

Implemented via AWSPE- 6467

The function is part of the StateMachineDynamodbBackup


sample event

{
    'TableName': '', 
    'TableArn': '', 
    'ParameterSetName': '',
    'TaskToken': ''
}


The function receives the trigger from the lambda processor.
It checks for the backup value in the parameter set table.
If "True" then the backup will be enabled. If "False" then the backup will be disabled.If "" (blank) then the backup process will be skipped on the table.
Upon successful completion, a success token will be sent and the report table will be updated.

    Author : Arunkumar Chandrasekar
    CreationDate : 15 Feb 2023
    ModifiedDate : 19 May 2023

'''

from botocore.config import Config
import os
import json
from boto_helper import boto_helper
boto_obj = boto_helper()

ddb_param_set_table = os.environ['MMDdbParamSetTableName']
ddb_rep_table = os.environ['MMDdbRepTableName']
dynamodb_log_group=os.environ['MMDdbLogGroupName']
dynamodb_log_stream=os.environ['MMDdbLogStreamName']

def lambda_handler(event, context):
    
    print('Received Event:',event)
    taskToken = event['TaskToken']
    tableName = event['TableName']
    tableArn = event['TableArn']
    parameterSetName = event['ParameterSetName']
    stateName = 'DynamodbBackup'
    error = {}
    error['TableArn'] = tableArn

    try:
        
        param_set_backup_check = boto_obj.get_param_set_backup_item(parameterSetName,ddb_param_set_table)
        
        if param_set_backup_check:
            bool_backup = boto_obj.str_to_bool(param_set_backup_check)
            print("Boolean_Backup -", bool_backup)
            
            print("######## Enable/Disable Backup has been started ########")
            backup_report = boto_obj.update_table_backup(tableName,bool_backup)
            print("######## Enable/Disable Backup has been completed ########")
            
            if 'success' in backup_report:
                payload_json = {'TableName':tableName, 'TableArn':tableArn, 'TaskToken':taskToken, 'StateMachine': stateName , 'Message': 'Enable/Disable backup is completed', 'ParameterSetName': parameterSetName}
                print("Sending success task status")
                boto_obj.handle_success(ddb_rep_table, tableName, stateName, 'Enable/Disable backup is completed', taskToken, payload_json, parameterSetName)
                boto_obj.put_log(dynamodb_log_group, dynamodb_log_stream, 'Enable/Disable backup is completed for the table {}'.format(tableName))
                boto_obj.put_log(dynamodb_log_group, tableName, 'Enable/Disable backup is completed for the table {}'.format(tableName))
            else:
                error['Error'] = 'Exception occured while performing Enable/Disable Backup'
                error['Cause'] = 'The update table backup has been failed'
                print("error", error)
                boto_obj.handle_failure(tableArn, ddb_rep_table, tableName, stateName, taskToken, error, parameterSetName)
                boto_obj.put_log(dynamodb_log_group, dynamodb_log_stream, 'The update table backup has been failed for the table {}'.format(tableName))
                boto_obj.put_log(dynamodb_log_group, tableName, 'The update table backup has been failed for the table {}'.format(tableName))                
            
        else:
            print("The backup tag value is BLANK. Hence no backup operation will be performed")
            payload_json = {'TableName':tableName, 'TableArn':tableArn, 'TaskToken':taskToken, 'StateMachine': stateName , 'Message': 'The backup tag value is BLANK.Hence the backup process is skipped', 'ParameterSetName': parameterSetName}
            boto_obj.handle_success(ddb_rep_table, tableName, stateName, 'The backup tag value is BLANK.Hence the backup process is skipped', taskToken, payload_json, parameterSetName)
            boto_obj.put_log(dynamodb_log_group, dynamodb_log_stream, 'The backup tag value is BLANK.Hence the backup process is skipped for the table {}'.format(tableName))
            boto_obj.put_log(dynamodb_log_group, tableName, 'The backup tag value is BLANK.Hence the backup process is skipped for the table {}'.format(tableName))            
            
    except Exception as e:
        print("Error-", e)
        error['Error'] = 'Exception occured while performing Enable/Disable Backup'
        error['Cause'] = 'The update table backup has been failed'
        boto_obj.handle_failure(tableArn, ddb_rep_table, tableName, stateName, taskToken, error, parameterSetName)
        boto_obj.put_log(dynamodb_log_group, dynamodb_log_stream, 'The update table backup has been failed for the table {}'.format(tableName))
        boto_obj.put_log(dynamodb_log_group, tableName, 'The update table backup has been failed for the table {}'.format(tableName))   
        raise