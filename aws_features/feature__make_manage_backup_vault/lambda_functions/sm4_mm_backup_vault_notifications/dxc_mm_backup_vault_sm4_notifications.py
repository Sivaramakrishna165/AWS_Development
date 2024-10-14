
'''
Implemented via AWSPE-6578, updated in AWSPE-6594
The function is part of the StateMachineBackupVault
State Machine Step 4 (sm4) - Notifications
sample event
{
    'BackupVaultName': '', 
    'ParameterSetName': '', 
    'TaskToken': ''
}
The function receives the trigger from state machine 3 (sm3) LockConfiguration
It checks  the BackupVaultEvents and BackupVaultSNSTopicArn attributes in the FtMMBackupVaultParameterSet Dynamodb table for the desired ParameterSetName. 
These represent the desired state of the vault for notifications.
The notification configuration provided in FtMMBackupVaultParameterSet DynamoDB table is verified against the notification configuration on the vault
  - If different, 
    - a check is made to determine which properties are different
    - non-dummy values in the database will be applied to the notification configuration on the vault.
  - If the same, then no changes will be applied to the notification configuration on the vault.
If both BackupVaultEvents = Dummy and BackupVaultSNSTopicArn = Dummy in FtMMBackupVaultParameterSet table
  - then the notification configurtion will removed from the vault
Upon successful completion, 
  - a success token will be sent to invoke the next state machine.
  - the report table will be updated with the corresponding StateDetail message StateSuccessFail (SUCCESS) message
If an error occurs,
  - a failure token will be sent to the step function, the remaining state machines will be skipped, and the reports state machine will be called to end the process.
  - the report table will be updated with the corresponding StateDetail error message StateSuccessFail (FAIL) message

'''

from botocore.config import Config
from botocore.exceptions import ClientError
import boto3
from boto3.dynamodb.conditions import Key
import os
import json

# required for boto3 responses containing datetime, tzlocal, and Decimal
from datetime import datetime
from dateutil.tz import tzlocal
from decimal import Decimal

config=Config(retries=dict(max_attempts=10,mode='standard'))
ddb = boto3.resource('dynamodb', config=config)
step_client = boto3.client('stepfunctions', config = config)
backup_client = boto3.client('backup', config = config)



def get_db_item(tbl_name, partition_key, partition_value, sort_key=None, sort_value=None):
    try:
        table = ddb.Table(tbl_name)
        if sort_key == None:
            get_item_response = table.get_item(Key={partition_key: partition_value})
        else:
            get_item_response = table.get_item(Key={partition_key: partition_value, sort_key: sort_value})
        print("get_item_response in get_db_item is ", get_item_response)
        return get_item_response
    except KeyError as e:
        print(str(e) + "KeyError exception in get_db_item")
        return 'Failed'

def add_db_items(tbl_name, obj_json):
    try:
        table = ddb.Table(tbl_name)
        print(obj_json)
        put_item_response = table.put_item(Item=obj_json)
        # print("put_item_response in add_db_items is ", put_item_response)
    except boto3.exceptions.botocore.client.ClientError as e:
        print("Error adding item: {}  - {}".format(obj_json, str(e)))
        raise


# Send task success to step function
def send_task_success(taskToken, payload_json):
    try:
        response = step_client.send_task_success(
            taskToken=taskToken,
            output = json.dumps(payload_json)
        )
        print('Task SUCCESS token sent - ',response)

    except Exception as e:
        print('Error send_task_success()-',e)


# Send task failure to step function
def send_task_failure(taskToken, error, cause):
    try:
        response = step_client.send_task_failure(
            taskToken=taskToken,
            error = error,
            cause = cause
        )
        print('Task FAILURE token sent - ',response)

    except Exception as e:
        print('Error send_task_failure()-',e)

def create_report_item(tbl_name, BackupVaultName, StateName, ParameterSetName, StateSuccessFail, StateDetail):
    # create a DynamoDB item in the FtMMBackupVaultReport table for the current state machine
    # each state machine has it's own entry
    # Partition key (BackupVaultName ) and Sort key (StateName )
    currentDT = datetime.now()
    date_time = currentDT.strftime('%m-%d-%Y_%H%M%S')
    #inst_rep_exists = check_db_entry_exists(tbl_name, 'InstanceId', instanceId)
    ddb_item_json = {
        "BackupVaultName": BackupVaultName,
        "StateName": StateName,
        "ParameterSetName": ParameterSetName,
        "CreationTime": date_time,
        "StateSuccessFail": StateSuccessFail,
        "StateDetail": StateDetail 
    }
    print("ddb_item_json in create_report_item is ", ddb_item_json)
    add_db_items(tbl_name, ddb_item_json)


def get_bkup_vault_notification(BackupVaultName):
    try:
        get_vault_notif_response = backup_client.get_backup_vault_notifications(
            BackupVaultName=BackupVaultName
        )

        print("get_vault_notif_response is ", get_vault_notif_response)
        return get_vault_notif_response

    except backup_client.exceptions.ResourceNotFoundException:
        #print("ClientError is ResourceNotFoundException")
        print("No Vault Notifications are set")
        return 'NoVaultNotifications'

    except Exception as e:
        print('Error in get_bkup_vault_notification()-',e)
        error = {}
        error['BackupVaultName'] = BackupVaultName
        error['Error'] = 'Error in get_bkup_vault_notification'
        error['Cause'] = str(e)
        return error


def put_bkup_vault_notification(BackupVaultName, BackupVaultSNSTopicArn, BackupVaultEvents, taskToken):
    try:
        print("putting backup vault notifications")
        put_bkup_vault_notif_response = backup_client.put_backup_vault_notifications(
            BackupVaultName=BackupVaultName,
            SNSTopicArn=BackupVaultSNSTopicArn,
            BackupVaultEvents=BackupVaultEvents
        )
        HttpStatus = put_bkup_vault_notif_response['ResponseMetadata']['HTTPStatusCode']
        print("HttpStatus in put_bkup_vault_notif_response is ", HttpStatus)
        if HttpStatus == 200 or HttpStatus == 202:
            StateSuccessFail = 'SUCCESS'
            return StateSuccessFail
        else:
            return 'FAIL'
    
    except Exception as e:
        print('Error in put_bkup_vault_notification()-',e)
        error = {}
        error['Error'] = 'Error in put_bkup_vault_notification'
        error['Cause'] = str(e)
        send_task_failure(taskToken, error['Error'], error['Cause'])
        StateSuccessFail = 'FAIL'
        return StateSuccessFail


def delete_bkup_vault_notifications(BackupVaultName, taskToken):
    try:
        del_bkup_vault_notif_response = backup_client.delete_backup_vault_notifications(
            BackupVaultName=BackupVaultName
        )
        # if response contains 200 or 202

        HttpStatus = del_bkup_vault_notif_response['ResponseMetadata']['HTTPStatusCode']
        print("HttpStatus in del_bkup_vault_notif_response is ", HttpStatus)
        if HttpStatus == 200 or HttpStatus == 202:
            StateDetail = 'Notifications Deleted'
            StateSuccessFail = 'SUCCESS'
            return StateDetail, StateSuccessFail
        else:
            return 'FAIL', 'FAIL'
      
    except Exception as e:
        print('Error in delete_vault_lock()-',e)
        error = {}
        error['Error'] = 'Error in delete_vault_lock'
        error['Cause'] = str(e)
        send_task_failure(taskToken, error['Error'], error['Cause'])
        StateDetail = str(e)
        StateSuccessFail = 'FAIL'
        return StateDetail, StateSuccessFail


def process_bkup_vault_notifications(BackupVaultName, db_BackupVaultSNSTopicArn, db_BackupVaultEvents, bkup_vault_response, taskToken):
    try:
        # depending on how put notificaitons works, might not need to process, just put whatever is in the db)
        print(" ")
        print("### processing backup vault notifications ###")
        print(" ")
        print("db_BackupVaultEvents is ", db_BackupVaultEvents)
        print(" ")
        print("db_BackupVaultSNSTopicArn is ", db_BackupVaultSNSTopicArn)
        print("bkup_vault_response in process_bkup_vault_notifications is ", bkup_vault_response)
        print(" ")

        if 'NoVaultNotifications' in bkup_vault_response:
            bkup_vault_events = False
        else:
            bkup_vault_events = bkup_vault_response['BackupVaultEvents']


        if 'SNSTopicArn' in bkup_vault_response:
            bkup_vault_topic_arn = bkup_vault_response['SNSTopicArn']
        else:
            bkup_vault_topic_arn = False

        print("bkup_vault_events is ", bkup_vault_events)
        if db_BackupVaultEvents == ['Dummy'] and db_BackupVaultSNSTopicArn == 'Dummy' and not bkup_vault_events:
            print("skip this state machine, nothing to do")
            StateDetail = 'Skipping, nothing to do'
            StateSuccessFail = 'SUCCESS' 
            return StateDetail, StateSuccessFail
        if db_BackupVaultEvents == ['Dummy'] and db_BackupVaultSNSTopicArn == 'Dummy' and bkup_vault_events:
            print("deleting notification event config from backup vault")
            StateDetail, StateSuccessFail = delete_bkup_vault_notifications(BackupVaultName, taskToken)
            return StateDetail, StateSuccessFail

        # compare db values against vault values and apply db values onto the vault if different
        if db_BackupVaultEvents != ['Dummy'] and db_BackupVaultSNSTopicArn != 'Dummy':
            StateDetail = 'Nothing to do'
            StateSuccessFail = 'SUCCESS'
            if not bkup_vault_events:
                print(" ")
                print("No vault notifications exist, putting db notifications")
                StateSuccessFail = put_bkup_vault_notification(BackupVaultName, db_BackupVaultSNSTopicArn, db_BackupVaultEvents, taskToken)
                if StateSuccessFail == 'SUCCESS':
                    StateDetail = 'Applied notifications to vault'
                    StateSuccessFail = 'SUCCESS' 
                else:
                    StateDetail = 'Failed to apply notifications to vault'
                    StateSuccessFail = 'FAIL' 
            else:
                if (db_BackupVaultEvents != bkup_vault_events):
                    print(" ")
                    print("applying event notifications from db onto the vault")
                    StateSuccessFail = put_bkup_vault_notification(BackupVaultName, db_BackupVaultSNSTopicArn, db_BackupVaultEvents, taskToken)
                    if StateSuccessFail == 'SUCCESS':
                        StateDetail = 'Applied notifications to vault'
                        StateSuccessFail = 'SUCCESS' 
                    else:
                        StateDetail = 'Failed to apply notifications to vault'
                        StateSuccessFail = 'FAIL' 
                else:
                    print("DB events and vault events are the same, nothing to do")
                    #StateDetail = 'Nothing to do'
                    #StateSuccessFail = 'SUCCESS' 
                if (db_BackupVaultSNSTopicArn != bkup_vault_topic_arn):
                    print("applying sns topic from db onto the vault")
                    StateSuccessFail = put_bkup_vault_notification(BackupVaultName, db_BackupVaultSNSTopicArn, db_BackupVaultEvents, taskToken)
                    if StateSuccessFail == 'SUCCESS':
                        StateDetail = 'Applied SNS topic ARN to vault'
                    else:
                        StateDetail = 'Failed to apply SNS topic ARN to vault'
                else:
                    print("DB sns topic and vault sns topic are the same, nothing to do")
        else:
            print("invalid attribute combination - missing events or topic arn")
            StateDetail = 'General Failure'
        return StateDetail, StateSuccessFail

    except Exception as e:
        print('Error in process_bkup_vault_notifications()-',e)
        error = {}
        error['Error'] = 'Error in process_bkup_vault_notifications'
        error['Cause'] = str(e)
        send_task_failure(taskToken, error['Error'], error['Cause'])
        StateDetail = str(e)
        StateSuccessFail = 'FAIL'
        return StateDetail, StateSuccessFail
   


def lambda_handler(event, context):
    
    print('Received Event:',event)
    taskToken = event['TaskToken']
    BackupVaultName = event['BackupVaultName']
    ParameterSetName = event['ParameterSetName']
    StateName = 'sm4-Notifications'
    print("inside sm4 - sm4-Notifications lambda") 

    success_payload_json = {
        'BackupVaultName': BackupVaultName,
        'ParameterSetName': ParameterSetName,
        'TaskToken':taskToken,
        'Message': 'LockConfiguration - Success'
    }

    fail_payload_json = {
        'BackupVaultName': BackupVaultName,
        'ParameterSetName': ParameterSetName,
        'TaskToken':taskToken,
        'Message': 'Notifications - Fail'
    }

    try:
        print("validating ParameterSetName")
        TableName = 'FtMMBackupVaultParameterSet'
        get_db_item_response = get_db_item(TableName, 'ParameterSetName', ParameterSetName) 
        print("get_db_item_response is ", get_db_item_response)
        if get_db_item_response != 'Failed':
            BackupVaultArn = get_db_item_response['Item']['BackupVaultArn']
            bkup_vault_response = get_bkup_vault_notification(BackupVaultName)
            db_BackupVaultEvents = get_db_item_response['Item']['BackupVaultEvents']
            db_BackupVaultSNSTopicArn = get_db_item_response['Item']['BackupVaultSNSTopicArn']
            StateDetail, StateSuccessFail = process_bkup_vault_notifications(BackupVaultName, db_BackupVaultSNSTopicArn, db_BackupVaultEvents, bkup_vault_response, taskToken)
            
            ## Print vault status summary to CloudWatch logs
            get_notif_response = get_bkup_vault_notification(BackupVaultName)
            print(" ")
            if get_notif_response != 'NoVaultNotifications':
                print("backup vault events after is ", get_notif_response['BackupVaultEvents'])
            else:
                print("the vault has no event notifications configured")
            if 'SNSTopicArn' in get_notif_response:
                bkup_vault_topic_arn = get_notif_response['SNSTopicArn']
            else:
                bkup_vault_topic_arn = False
            if bkup_vault_topic_arn:
                print("snt topic arn after is ", bkup_vault_topic_arn)
            else:
                print("the vault has no sns topics configured")

            # update the state machine for sm4
            if StateSuccessFail == 'SUCCESS':
                send_task_success(taskToken, success_payload_json)
            else:
                send_task_failure(taskToken, 'sm4-VaultNotifications failed', 'sm4-VaultNotifications failed')

            #update the report table for sm4
            TableName = 'FtMMBackupVaultReport'
            create_report_item(TableName, BackupVaultName, StateName, ParameterSetName, StateSuccessFail, StateDetail)

        else:
            # Add Failure message to the report table for sm4
            StateSuccessFail = 'FAIL'
            StateDetail = 'No config to apply'
            TableName = 'FtMMBackupVaultReport'
            create_report_item(TableName, BackupVaultName, StateName, ParameterSetName, StateSuccessFail, StateDetail)
            # Abort make manage, no database values to check
            send_task_failure(taskToken, 'sm4-VaultNotifications failed', 'sm4-VaultNotifications failed')
            
    except Exception as e:
        print("Error-", e)
        raise
