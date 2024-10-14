'''

#Implemented via AWSPE- 6469

#The function is part of the StateMachineDynamodbAlarms

#The function receives the trigger from the lambda function of the statemachine2 (StateMachineDynamodbEncryption).
#It checks for the alarm tag value in the Dynamodb param set table.
#If "True" then the default alarms will be created. If "False" then the alarms will be deleted..
#Upon successful completion, a success token will be sent and the report table will be updated.

sample event

{
    'TableName': '', 
    'TableArn': '', 
    'TaskToken': '',
    'ParameterSetName': ''
}

    Author : Arunkumar Chandrasekar
    CreationDate : 21 Feb 2023
    ModifiedDate : 19 May 2023

'''

from botocore.config import Config
import os
import json
from boto_helper import boto_helper
boto_obj = boto_helper()

ddb_param_set_table = os.environ['MMDdbParamSetTableName']
ddb_rep_table = os.environ['MMDdbRepTableName']
ddb_alarm_table = os.environ['MMDdbAlarmsTableName']
alarm_topic = os.environ['CommonIncidentTopic']
dynamodb_log_group=os.environ['MMDdbLogGroupName']
dynamodb_log_stream=os.environ['MMDdbLogStreamName']

def lambda_handler(event, context):
    
    print('Received Event:',event)
    taskToken = event['TaskToken']
    tableName = event['TableName']
    tableArn = event['TableArn']
    parameterSetName = event['ParameterSetName']    
    stateName = 'DynamodbAlarms'

    error = {}
    error['TableArn'] = tableArn
    
    try:
        
        param_set_alarm_check = boto_obj.get_param_set_alarm_item(parameterSetName,ddb_param_set_table)
        
        if param_set_alarm_check:
            
            if param_set_alarm_check.lower() == "true":
                print("The alarm tag is set as TRUE")
                default_alarms_check = boto_obj.check_db_entry_exists(ddb_alarm_table, 'TableName', tableName)
                default_alarms=default_alarms_check['Alarms']
                print("Default_alarms", default_alarms)
                
                if(default_alarms):
                    
                    for alarm in default_alarms:
                        
                        alarm_params = {}
                        
                        for dim in alarm['Dimensions']:
                            if dim['Name']=='TableName':
                                dim['Value']=tableName
                            
                        alarm_name='_'.join(["MM",alarm['Namespace'].lower().replace("/",""),dim['Value'],alarm['MetricName']])
                        
                        alarm_check_result=boto_obj.alarm_check(alarm_name)
                        
                        if not alarm_check_result:
                            
                            alarm_params['AlarmName']=alarm_name
                            if('AlarmActions' in alarm and len(alarm['AlarmActions']) == 0):
                                alarm_params['AlarmActions']=[alarm_topic]
                            alarm_params['ActionsEnabled']= alarm['ActionsEnabled']
                            alarm_params['AlarmDescription']= alarm['AlarmDescription']
                            alarm_params['ComparisonOperator']=alarm['ComparisonOperator']
                            alarm_params['Dimensions']=alarm['Dimensions']
                            alarm_params['EvaluationPeriods']=int(alarm['EvaluationPeriods'])
                            alarm_params['MetricName']=alarm['MetricName']
                            alarm_params['Namespace']=alarm['Namespace']
                            alarm_params['Period']=int(alarm['Period'])
                            alarm_params['Statistic']=alarm['Statistic']
                            alarm_params['Threshold']=int(alarm['Threshold'])
                            
                            boto_obj.create_alarm(**alarm_params)
                    
                    print("The alarm creation process completed successfully")
                    payload_json = {'TableName':tableName, 'TableArn':tableArn, 'TaskToken':taskToken, 'StateMachine': stateName , 'Message': 'The alarm creation process completed successfully', 'ParameterSetName': parameterSetName}
                    boto_obj.handle_success(ddb_rep_table, tableName, stateName, 'The alarm creation process completed successfully', taskToken, payload_json, parameterSetName)
                    boto_obj.put_log(dynamodb_log_group, dynamodb_log_stream, 'The alarm creation process completed successfully for the table {}'.format(tableName))
                    boto_obj.put_log(dynamodb_log_group, tableName, 'The alarm creation process completed successfully for the table {}'.format(tableName))
                            
                else:
                    error['Error'] = 'Exception occured while creating alarm'
                    error['Cause'] = 'The default alarms are not available in the alarm table' 
                    print("Error - The alarm tag is set to TRUE but the default alarms are not available in the alarm table {}".format(ddb_alarm_table))
                    boto_obj.handle_failure(tableArn, ddb_rep_table, tableName, stateName, taskToken, error, parameterSetName)
                    boto_obj.put_log(dynamodb_log_group, dynamodb_log_stream, 'The alarm tag is set to TRUE but the default alarms are not available in the alarm table {}'.format(tableName))
                    boto_obj.put_log(dynamodb_log_group, tableName, 'The alarm tag is set to TRUE but the default alarms are not available in the alarm table {}'.format(tableName))
                    
            elif param_set_alarm_check.lower() == "false":
                print("The alarm tag is set as FALSE")
                default_alarms_check = boto_obj.check_db_entry_exists(ddb_alarm_table, 'TableName', tableName)
                default_alarms=default_alarms_check['Alarms']
                print("Default_alarms", default_alarms)
                
                if(default_alarms):
                    
                    for alarm in default_alarms:
                        
                        alarm_params = {}
                        
                        for dim in alarm['Dimensions']:
                            if dim['Name']=='TableName':
                                dim['Value']=tableName
                            
                        alarm_name='_'.join(["MM",alarm['Namespace'].lower().replace("/",""),dim['Value'],alarm['MetricName']])
                        
                        alarm_check_result=boto_obj.alarm_check(alarm_name)
                        
                        if alarm_check_result:
                            boto_obj.delete_alarm(alarm_name)
                            
                    print("The alarm deletion process completed successfully")
                    payload_json = {'TableName':tableName, 'TableArn':tableArn, 'TaskToken':taskToken, 'StateMachine': stateName , 'Message': 'The alarm deletion process completed successfully', 'ParameterSetName': parameterSetName}
                    boto_obj.handle_success(ddb_rep_table, tableName, stateName, 'The alarm deletion process completed successfully', taskToken, payload_json, parameterSetName)
                    boto_obj.put_log(dynamodb_log_group, dynamodb_log_stream, 'The alarm deletion process completed successfully for the table {}'.format(tableName))
                    boto_obj.put_log(dynamodb_log_group, tableName, 'The alarm deletion process completed successfully for the table {}'.format(tableName))
                    
                else:
                    print("The alarm tag is set to FALSE but the default alarms are not available in the alarm table {}".format(ddb_alarm_table))
                    payload_json = {'TableName':tableName, 'TableArn':tableArn, 'TaskToken':taskToken, 'StateMachine': stateName , 'Message': 'The alarm tag is set to FALSE but the default alarms are not available in the alarm table', 'ParameterSetName': parameterSetName}
                    boto_obj.handle_success(ddb_rep_table, tableName, stateName, 'The alarm tag is set to FALSE but the default alarms are not available in the alarm table', taskToken, payload_json, parameterSetName)
                    boto_obj.put_log(dynamodb_log_group, dynamodb_log_stream, 'The alarm tag is set to FALSE but the default alarms are not available in the alarm table {}'.format(tableName))
                    boto_obj.put_log(dynamodb_log_group, tableName, 'The alarm tag is set to FALSE but the default alarms are not available in the alarm table {}'.format(tableName))                
                            
            else:
                error['Error'] = 'Exception occurred while validating alarm tag'
                error['Cause'] = 'The alarm tag value is invalid'
                print("The alarm tag value is invalid - {}. Hence no alarms are created for table - {}".format(param_set_alarm_check, tableName))
                boto_obj.handle_failure(tableArn, ddb_rep_table, tableName, stateName, taskToken, error, parameterSetName)
                boto_obj.put_log(dynamodb_log_group, dynamodb_log_stream, 'The alarm tag value is invalid - {}. Hence no alarms are created for table - {}'.format(param_set_alarm_check, tableName))
                boto_obj.put_log(dynamodb_log_group, tableName, 'The alarm tag value is invalid - {}. Hence no alarms are created for table - {}'.format(param_set_alarm_check, tableName))                
        else:
            print("The alarm tag value is BLANK. Hence no alarms created for table - {}".format(tableName))
            payload_json = {'TableName':tableName, 'TableArn':tableArn, 'TaskToken':taskToken, 'StateMachine': stateName , 'Message': 'The alarm tag value is BLANK. Hence no alarms created', 'ParameterSetName': parameterSetName}
            boto_obj.handle_success(ddb_rep_table, tableName, stateName, 'The alarm tag value is BLANK. Hence no alarms are created', taskToken, payload_json, parameterSetName)
            boto_obj.put_log(dynamodb_log_group, dynamodb_log_stream, 'The alarm tag value is BLANK. Hence no alarms are created for the table {}'.format(tableName))
            boto_obj.put_log(dynamodb_log_group, tableName, 'The alarm tag value is BLANK. Hence no alarms are created for the table {}'.format(tableName))            
            
    except Exception as e:
        print(e)
        error['Error'] = 'Exception occured while creating alarm'
        error['Cause'] = 'The alarm creation process failed'
        boto_obj.handle_failure(tableArn, ddb_rep_table, tableName, stateName, taskToken, error, parameterSetName)
        boto_obj.put_log(dynamodb_log_group, dynamodb_log_stream, 'Exception occured while creating alarm for the table {}'.format(tableName))
        boto_obj.put_log(dynamodb_log_group, tableName, 'Exception occured while creating alarm for the table {}'.format(tableName))
        raise