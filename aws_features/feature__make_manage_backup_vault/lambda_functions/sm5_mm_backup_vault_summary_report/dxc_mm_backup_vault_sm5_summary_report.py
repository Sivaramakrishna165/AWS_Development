'''
Implemented via AWSPE-6578
The function is part of the StateMachineBackupVault

This is the final statemachine in the stepfunction. 
The state machine 5 triggers upon completion of the state machine 4 or upon failure of any statemachine in the the stepfunction.
On a success scenario the dxc_backupvault_make_manage tag will be set to "Managed". On a Failure scenario the dxc_backupvault_make_manage tag will be set to "Fail"
A report will be generated and sent to S3 customer bucket.
'''
"""
success_event:{
    'BackupVaultName': '',
    'ParameterSetName': '',
    'TaskToken': '', 
}
failed_event:{
    'BackupVaultName':'',
    'Error':'',
    'Cause':'',   
}

"""

import boto3
from botocore.config import Config
import os
import json
from datetime import datetime
import csv
import codecs

def send_task_success(client,taskToken, payload_json):
    try:
        response = client.send_task_success(
            taskToken=taskToken,
            output = json.dumps(payload_json)
        )
        print('Task SUCCESS token sent - ',response)

    except Exception as e:
        print('Error send_task_success()-',e)


def update_tag(client,Arn,key,status):
    if status=="SUCCESS":
        value='Managed'
    else:
        value='Fail'
    
    try:
        
        update_tag_response = client.tag_resource(
            ResourceArn= Arn,
            Tags=
                {
                    key:value
                }
        )
        
        print("update_tag_response is ", update_tag_response)
        
    except Exception as e:
        print("Error in update_tag", e)

def update_report_table(ddb,nb_rep_table,state_name,vault_name,status,statedetail):
    try:
        table = ddb.Table(nb_rep_table)
        currentDT = datetime.now()
        date_time = currentDT.strftime('%m-%d-%Y_%H%M%S')
        
        table.update_item(
            Key={
                'BackupVaultName': vault_name,
                'StateName': state_name
            },
            UpdateExpression='SET CreationTime=:time, StateSuccessFail=:status, StateDetail=:statedetail',
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

def get_table_report_data(ddb,nb_rep_table,vaultName,state_name):
    try:
        table = ddb.Table(nb_rep_table)
        response = table.get_item(Key={
                'BackupVaultName': vaultName,
                'StateName': state_name
            })
        print("successfully retrieved the data from report table")
        table_report_data = response['Item']
        print("Table Report Data-", table_report_data)
        return table_report_data
    
    except Exception as e:
        print("Error in fetching the data from report table", e)
        raise
def get_parameter(ssm_client,param_name):
    try:
        response = ssm_client.get_parameter(Name = param_name,WithDecryption=True)['Parameter']['Value']
        print("Response-", response)
        return response
    except Exception as e:
        print("Error-",e)
        raise
def read_s3_object(s3_client,bucket, key):
    try:
        data = s3_client.get_object(Bucket=bucket, Key=key)
        return data
    except Exception as e:
        print('Error read_s3_object() -',e)
        raise
def upload_file(s3_resource,tmpfile,customer_bucket,location):
    try:
        response=s3_resource.meta.client.upload_file(tmpfile,customer_bucket,location)
    except Exception as e:
        print("Error -", e)
        raise

def lambda_handler(event, context):
    try:
        print('Received Event:',event)
        states=["sm1-AccessPolicy","sm2-BackupVaultTags","sm3-LockConfiguration","sm4-Notifications"]
        backup_vault_name = event['BackupVaultName']
        state_name="sm5-BackupVaultSummaryReport"
        status='SUCCESS'
        if "Payload" in event:
            if "Error" in event["Payload"]:
                error=event["Payload"]['Error']
                cause=event["Payload"]['Cause']
                status="Fail"
                statedetail=cause
                parameter_set_name = event['ParameterSetName']
        else:
            parameter_set_name = event['ParameterSetName']
            task_token = event['TaskToken']
            statedetail = 'The make manage process has been completed successfully'
        
        config = Config(retries=dict(max_attempts=10,mode='standard'))
        ddb = boto3.resource('dynamodb', config=config)
        step_client = boto3.client('stepfunctions', config=config)
        vault_client=boto3.client('backup', config=config)
        ssm_client=boto3.client('ssm', config=config)
        s3_client=boto3.client('s3', config=config)
        s3_resource=boto3.resource('s3', config=config)
        
        nb_rep_table = os.environ['MMNBRepTableName']
        customer_bucket = os.environ['pDXCS3CustomerBucketName']
        output_location = os.environ['MMNBOutputLocation']
             
        update_tag(vault_client,"arn:aws:backup:"+os.environ["AWS_REGION"]+":"+context.invoked_function_arn.split(":")[4]+":backup-vault:"+str(backup_vault_name), 'dxc_backupvault_make_manage', status)
        
        #qa (ddb,nb_rep_table, state_name, backup_vault_name, status, statedetail)
        currentDT = datetime.now()
        date_time = currentDT.strftime('%m-%d-%Y_%H%M%S')
        table_report_data=[]
        check=1
        for state in states:
            
            if check==1:
                table_report_data.append(get_table_report_data(ddb,nb_rep_table,backup_vault_name,state))
                if "Message" in event:
                    
                    if state[4:] == event["Message"].replace(" - Success",""):
                        if state!=states[-1]:
                            table_report_data.append(get_table_report_data(ddb,nb_rep_table,backup_vault_name,states[int(states.index(state))+1]))
                            check=0
                elif states[0]==state:
                    check=0
                    

                
        #table_report_data=get_table_report_data(ddb,nb_rep_table,backup_vault_name,state_name)
        keys=table_report_data[0].keys()
        print("Keys-", keys)
        
        location = get_parameter(ssm_client,output_location)
        output_folder = '/'.join(location.split('/')[:-1])
        output_file_name = location.split('/')[-1]
        
        table_csv_data=[]
        
        try:
            
            table_csv_data=read_s3_object(s3_client,customer_bucket,location)
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
                for item_row in table_report_data:
                    dict_writer.writerows([item_row])
            except Exception as e:
                print("Error-", e)
                raise
            
        tmpfile = '/tmp/'+output_file_name
        
        print("############################# UPLOAD STARTED #########################")
        upload_file_to_s3=upload_file(s3_resource,tmpfile,customer_bucket,location)
        os.remove(tmpfile)
        print("############################# UPLOAD ENDED #########################")
        
        
        
        #stateName = 'AccessPolicy'
        #error = {}
        #error['TableArn'] = tableArn


        #print("inside summary report sm5 lambda")
        

        #send task success to Task Token
        if 'TaskToken' in event:
            payload_json = {
            'BackupVaultName': backup_vault_name,
            'ParameterSetName': parameter_set_name,
            'TaskToken':task_token,
            'Message': 'Repport - Success'
            }
            send_task_success(step_client,task_token, payload_json)
        else:
            raise "Error"


    except Exception as e:
        print("Error-", e)
        raise
