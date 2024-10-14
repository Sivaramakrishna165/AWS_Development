'''
Implemented as part [AWSPE-6471]

This is the final statemachine in the stepfunction. 
The state machine 4 triggers upon completion of the state machine 3 or upon failure of any statemachine in the the stepfunction.
On a success scenario the dxc_dynamodb_makemanage tag will be set to "Managed". On a Failure scenario the dxc_dynamodb_makemanage tag will be set to "Fail"
A report will be generated and sent to S3 customer bucket.

Success event:

{
    'TableName': '', 
    'TableArn': '', 
    'TaskToken': '',
    'StateMachine': '',
    'Message': ''
}

Failure Event:

{
    'Error':'',
    'Cause':''
}

    
    Author : Arunkumar Chandrasekar
    CreationDate : 6th March 2023
    ModifiedDate : 19th May 2023


'''

import boto3 
import json
import os
import csv
import codecs
from boto_helper import boto_helper
boto_obj = boto_helper()

ddb_param_set_table = os.environ['MMDdbParamSetTableName']
ddb_rep_table = os.environ['MMDdbRepTableName']
customer_bucket = os.environ['pDXCS3CustomerBucketName']
output_location = os.environ['MMDdbOutputLocation']
last_state_name = os.environ['MMDdbLastStateName']
dynamodb_log_group=os.environ['MMDdbLogGroupName']
dynamodb_log_stream=os.environ['MMDdbLogStreamName']

def lambda_handler(event, context):
    try:
        print('Event - ', event)
        print('Context - ', context)
        status = "SUCCESS"
        error_message = ''
        
        if('Error' in event):
            try:
                error_json = json.loads(event['Error'])
            except Exception as e:
                print('Not Valid Json Format', str(e))
                error_json = event['Error']
            tableArn = error_json['TableArn']
            tableName = error_json['TableArn'].split("/")[1]
            error_message = "For " +  tableName + " : STEP : " + error_json['Error']  + ' Cause : ' + event['Cause']
            status = "FAIL"
            statedetail = error_json['Cause']
            print("Error message",error_message)
            
        if('TaskToken' in event):
            taskToken = event['TaskToken']
            tableArn = event['TableArn']
            tableName = event['TableArn'].split("/")[1]            
            statedetail = 'The make manage process has been completed successfully'
            
        boto_obj.update_tag(tableArn, 'dxc_dynamodb_make_manage', status)
        boto_obj.update_report_table(ddb_rep_table, tableName, status, statedetail)
        
        table_report_data=boto_obj.get_table_report_data(ddb_rep_table,tableName)
        keys=table_report_data.keys()
        print("Keys-", keys)
        
        location = boto_obj.get_parameter(output_location)
        output_folder = '/'.join(location.split('/')[:-1])
        output_file_name = location.split('/')[-1]
        
        table_csv_data=[]
        try:
            
            table_csv_data=boto_obj.read_s3_object(customer_bucket,location)
            print("Table CSV Data-", table_csv_data)
            
        except Exception as e:
            print("Error", e)
        
        with open('/tmp/'+output_file_name, 'a', newline='') as output_file:
            dict_writer = csv.DictWriter(output_file, keys)
            dict_writer.writeheader()
            try:
                if table_csv_data:
                    for row in csv.DictReader(codecs.getreader("utf-8")(table_csv_data["Body"])):
                        print("Existing Row-",row)
                        dict_writer.writerows([row])
                dict_writer.writerows([table_report_data])
            except Exception as e:
                print("Error-", e)
                raise
        
        print("Customer bucket is ", customer_bucket)
        print("Output folder is ", output_folder)
        print("S3 path is ", location)
        print("File name is is ", output_file_name)
        tmpfile = '/tmp/'+output_file_name
        print("tmpfile is ", tmpfile)
        print("############################# UPLOAD STARTED #########################")
        upload_file_to_s3=boto_obj.upload_file(tmpfile,customer_bucket,location)
        os.remove(tmpfile)
        print("############################# UPLOAD ENDED #########################")
        boto_obj.put_log(dynamodb_log_group, dynamodb_log_stream, 'Report has been updated successfully for the table {}'.format(tableName))
        boto_obj.put_log(dynamodb_log_group, tableName, 'Report has been updated successfully for the table {}'.format(tableName))          
        
    except Exception as e:
        print("Exception occured during lambda execution", e)
        boto_obj.put_log(dynamodb_log_group, dynamodb_log_stream, 'Exception occured while generating report for the table {}'.format(tableName))
        boto_obj.put_log(dynamodb_log_group, tableName, 'Exception occured while generating report for the table {}'.format(tableName))
        raise