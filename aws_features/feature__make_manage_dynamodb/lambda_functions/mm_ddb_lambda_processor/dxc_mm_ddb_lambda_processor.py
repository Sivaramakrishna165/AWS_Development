'''
#Implemented via AWSPE- 6466

# The trigger event is based on the create/update of the tag dxc_dynamodb_make_manage to true/True/TRUE in the Dynamodb tables

# Once the event is received, the function will process the same.
# Extracts the tablearn and tablename from the event.
# Validate the dxc_dynamodb_make_manage tage is TRUE/True/true
# Once the tag is validated the below tables will be updated
#       FtMMDynamodbParameterSet - Dynamo db table name with the tag information will be updated in this param set table. 
#       FtMMDynamodbAlarms - Dynamo db table alarm properties will be loaded in this alarm table.
#       FtMMDynamodbReport - The current status information will be updated in this report table.
# Once the tables are successfully loaded, the step function will be invoked.

sample event:

{
   "resources":[""],
   "detail":{
      "tags":{
         "dxc_dynamodb_make_manage":"TRUE"
		 "dxc_dynamodb_parameter_set" : "Default"
      }
   }
}

    Author : Arunkumar Chandrasekar
    CreationDate : 09 Feb 2023
    ModifiedDate : 19 May 2023

'''

from botocore.config import Config
import os
import json
from boto_helper import boto_helper
boto_obj = boto_helper()

ddb_param_set_table = os.environ['MMDdbParamSetTableName']
ddb_alarms_table = os.environ['MMDdbAlarmsTableName']
ddb_rep_table = os.environ['MMDdbRepTableName']
state_fun_arn = os.environ['StateFunArn']
dynamodb_log_group=os.environ['MMDdbLogGroupName']
dynamodb_log_stream=os.environ['MMDdbLogStreamName']

#Load the MakeManage - Dynamodb default alarms
f = open('default_ddb_table_alarms.json') 
default_ddb_table_alarm = json.load(f)

#To validate the tags recevied from the user created table.
def validate_event(event):
    result_json = {
        'tablename': 'None',
        'tags_valid':'False',
        'dxc_dynamodb_make_manage':'None',
        'dxc_dynamodb_parameter_set':'None',
        'tablearn':'None'
    }
    
    TableArn = event['resources'][0]
    print("The table arn is -", TableArn)
    
    TableName = TableArn.split("/")[1]
    print("The table name is -", TableName)
    
    result_json['tablename'] = TableName
    result_json['tablearn'] = TableArn
    
    tags = event['detail']['tags']
    print("The tags are -", tags)
    
    dxc_dynamodb_make_manage = tags['dxc_dynamodb_make_manage']
    
    try:
        
        if dxc_dynamodb_make_manage.lower() == 'true' and 'dxc_dynamodb_parameter_set' in tags:
            result_json['dxc_dynamodb_make_manage'] = dxc_dynamodb_make_manage
            result_json['dxc_dynamodb_parameter_set'] = tags['dxc_dynamodb_parameter_set']
            result_json['tags_valid'] = 'True'
            print("The dxc_dynamodb_make_manage tag is -", dxc_dynamodb_make_manage)
            
        else:
            print("Error - Invalid tag value")
            result_json['tags_valid'] = 'Invalid tag value'            
            
    except Exception as e:
        result_json['tags_valid'] = e
        print("Error", e)     
        
    return result_json
    
def lambda_handler(event, context):
    print('Received Event:',event)
    event_results_json = validate_event(event)
    tableArn = event_results_json['tablearn']
    tableName = event_results_json['tablename']
    
    if event_results_json['tags_valid'] == 'True':
        print("event_results_json from handler is ", event_results_json)
        parameterSetName = event_results_json['dxc_dynamodb_parameter_set']
        
        param_set_item_exists = boto_obj.check_db_entry_exists(ddb_param_set_table, 'ParameterSetName', 'Default')
        if not param_set_item_exists:
            param_set_item_json = boto_obj.create_ddb_table_param_set_item()
            if param_set_item_json:
                boto_obj.add_items(ddb_param_set_table,param_set_item_json)
        else:
            print("Default item already available in the param set table {}. Hence, no update.".format(ddb_param_set_table))
            
        alarm_item_exists = boto_obj.check_db_entry_exists(ddb_alarms_table, 'TableName', tableName)
        if not alarm_item_exists:
            alarm_item_json = boto_obj.create_ddb_table_alarm_item(event_results_json,default_ddb_table_alarm)
            if alarm_item_json:
                boto_obj.add_items(ddb_alarms_table,alarm_item_json)
        else:
            print("{} item already available in the alarm table {}. Hence, no update.".format(tableName,ddb_alarms_table))
        
        report_item_exists = boto_obj.check_db_entry_exists(ddb_rep_table, 'TableName', tableName)
        if not report_item_exists:
            report_item_json = boto_obj.create_ddb_table_report_item(event_results_json)
            if report_item_json:
                boto_obj.add_items(ddb_rep_table,report_item_json)
        else:
            print("{} item already available in the report table {}. Hence, no update.".format(tableName,ddb_rep_table))
        
        boto_obj.update_tag(tableArn,'dxc_dynamodb_make_manage','InProgress')
            
        validate_parameterset = boto_obj.check_db_entry_exists(ddb_param_set_table, 'ParameterSetName', parameterSetName)
        if validate_parameterset:
            print('ParameterSetName {} from tag has been located in the ParameterSet table'.format(parameterSetName))
        else:
            raise Exception('Error: ParameterSetName {} from the tag does not exist in the ParameterSet database, aborting make manage.'.format(parameterSetName))
        
        input = {}
        input['TableName'] = tableName
        input['TableArn'] = tableArn
        input['ParameterSetName'] = parameterSetName
        state_machine_input = json.dumps(input)
        print("calling the statemachine")
        boto_obj.call_state_machine(state_machine_input, state_fun_arn)
        boto_obj.put_log(dynamodb_log_group, dynamodb_log_stream, 'Make Manage process has been started for the table {}'.format(tableName))
        boto_obj.put_log(dynamodb_log_group, tableName, 'Make Manage process has been started for the table {}'.format(tableName))           
    else:
        print("EVENT JSON-", event_results_json)
        error_message = event_results_json['tags_valid']
        print("Processing failed Due to INVALID TAGS : ", error_message)
        boto_obj.update_tag(tableArn,'dxc_dynamodb_make_manage','Fail')
        
        report_item_json = boto_obj.create_ddb_table_report_item_failure(event_results_json,'Processor','Fail')
        if report_item_json:
            boto_obj.add_items(ddb_rep_table,report_item_json)
            
        boto_obj.put_log(dynamodb_log_group, dynamodb_log_stream, 'Processing failed Due to INVALID TAGS - {} in the table {}'.format(error_message,tableName))
        boto_obj.put_log(dynamodb_log_group, tableName, 'Processing failed Due to INVALID TAGS - {} in the table {}'.format(error_message,tableName))