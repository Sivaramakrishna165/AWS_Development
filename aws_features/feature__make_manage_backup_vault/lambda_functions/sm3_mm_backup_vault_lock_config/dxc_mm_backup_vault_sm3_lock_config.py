
'''
Implemented via AWSPE-6578, updated in AWSPE-6594
The function is part of the StateMachineBackupVault
State Machine Step 3 (sm3) - LockConfiguration
sample event
{
    'BackupVaultName': '', 
    'ParameterSetName': '', 
    'TaskToken': ''
}
The function receives the trigger from state machine 2 (sm2) BackupVaultTags
It checks  the BackupVaultChangeableForDays , BackupVaultMaxRetentionDays, and BackupVaultMinRetentionDays attributes in the FtMMBackupVaultParameterSet Dynamodb table for the desired ParameterSetName. 
These represent the desired state (lock configuration) of the vault.
Since boto3 requires integers, default "Dummy" text values of '36499' are used in the database, indicating no action will be taken.
The lock configuration provided in DynamoDB is verified against the lock configuration on the vault
  - If different, 
    - a check is made to determine which properties are different
    - non-dummy values in the database will be applied to the lock configuration on the vault.
  - If the same, then no changes will be applied to the lock configuration on the vault.
If "Dummy" (36499)  then no changes will be applied to the lock configuration on the vault.
If all three vault lock parameters BackupVaultMinRetentionDays, BackupVaultMaxRetentionDays, and BackupVaultChangeableForDays are set to the dummy value 36499, 
  - then the lock will removed from the vault
Note: since AWS reports Compliance mode with a grace period which counts down each day, if mm is run again with the same BackupVaultChangeableForDays value:
  - the grace period starts over with current value.  Adjust this value before running if the same date is desired.
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


def get_vault_lock_config(BackupVaultName):
    try:
        print("retrieving vault config")
        describe_backup_vault_response = backup_client.describe_backup_vault(
            BackupVaultName=BackupVaultName
        )
        print("describe_backup_vault_response is ", describe_backup_vault_response)

        vault_lock_config = {}
        try:
            if 'Locked' in describe_backup_vault_response:
                vault_lock_config['VaultLocked'] = int(describe_backup_vault_response['Locked'])
        except KeyError as e:
            print("Key: Locked not present")
            vault_lock_config['VaultLocked'] = None
        
        try:
            if 'MinRetentionDays' in describe_backup_vault_response:
                vault_lock_config['VaultMinRetentionDays'] = int(describe_backup_vault_response['MinRetentionDays'])
        except KeyError as e:
            print("Key: MinRetentionDays not present")
            vault_lock_config['MinRetentionDays'] = None
        
        try:
            if 'MaxRetentionDays' in describe_backup_vault_response:
                vault_lock_config['VaultMaxRetentionDays'] = int(describe_backup_vault_response['MaxRetentionDays'])
        except KeyError as e:
            print("Key: MaxRetentionDays not present")
            vault_lock_config['MaxRetentionDays'] = None
        
        try:
            if 'LockDate' in describe_backup_vault_response:
                print("LockDate is ", describe_backup_vault_response['LockDate'])
                print("Type of LockDate is ", type(describe_backup_vault_response['LockDate']))
                if isinstance(describe_backup_vault_response['LockDate'], datetime):
                    #if type(describe_backup_vault_response['LockDate']) == datetime:
                    print("## TYPE IS DATE ##")
                    vault_lock_config['VaultLockDate'] = '34698'
                #else:
                #    print("### TYPE NOT DATE ###")
                #    vault_lock_config['VaultLockDate'] = int(describe_backup_vault_response['LockDate'])
        except KeyError as e:
            print("Key: LockDate not present")
            vault_lock_config['LockDate'] = None
        
        print("vault_lock_config is ", vault_lock_config)
        return vault_lock_config

    except Exception as e:
        print('Error in get_vault_lock_config()-',e)
        error = {}
        error['BackupVaultName'] = BackupVaultName
        error['Error'] = 'Error in get_vault_lock_config'
        error['Cause'] = str(e)
        return error

def update_vault_lock(backup_vault_name, desired_lock_config, taskToken):

    print("desired_lock_config in update_vault_lock is ", desired_lock_config)
    print("type of desired_lock_config is ", type(desired_lock_config))
    BackupVaultName = backup_vault_name 
    MinRetentionDays=None
    MaxRetentionDays=None
    ChangeableForDays=None
    
    try:
        if 'BackupVaultMinRetentionDays' in desired_lock_config and len(desired_lock_config) == 1:
            try:
                MinRetentionDays = int(desired_lock_config['BackupVaultMinRetentionDays'])
                print("adding only MinRetentionDays")
                do_response = backup_client.put_backup_vault_lock_configuration(
                    BackupVaultName=BackupVaultName,
                    MinRetentionDays=MinRetentionDays
                )
            except Exception as e:
                print("Error, min not found, continuing", e)
                pass
        elif 'BackupVaultMinRetentionDays' in desired_lock_config and 'BackupVaultMaxRetentionDays' in desired_lock_config and len(desired_lock_config) == 2:
            try:
                MinRetentionDays = int(desired_lock_config['BackupVaultMinRetentionDays'])
                MaxRetentionDays = int(desired_lock_config['BackupVaultMaxRetentionDays'])
                print("adding MinRetentionDays and MaxRetentionDays")
                do_response = backup_client.put_backup_vault_lock_configuration(
                    BackupVaultName=BackupVaultName,
                    MinRetentionDays=MinRetentionDays,
                    MaxRetentionDays=MaxRetentionDays
                )
            except Exception as e:
                print("Error, min and max not found, continuing", e)
                pass
        elif 'BackupVaultMaxRetentionDays' in desired_lock_config and len(desired_lock_config) == 1:
            try:
                MaxRetentionDays = int(desired_lock_config['BackupVaultMaxRetentionDays'])
                print("adding MaxRetentionDays")
                do_response = backup_client.put_backup_vault_lock_configuration(
                    BackupVaultName=BackupVaultName,
                    MaxRetentionDays=MaxRetentionDays
                )
            except Exception as e:
                print("Error, max not found, continuing", e)
                pass
        elif 'BackupVaultMinRetentionDays' in desired_lock_config and 'BackupVaultMaxRetentionDays' in desired_lock_config and 'BackupVaultChangeableForDays' in desired_lock_config and len(desired_lock_config) == 3:
            try:
                MinRetentionDays = int(desired_lock_config['BackupVaultMinRetentionDays'])
                MaxRetentionDays = int(desired_lock_config['BackupVaultMaxRetentionDays'])
                ChangeableForDays = int(desired_lock_config['BackupVaultChangeableForDays'])
                print("adding MinRetentionDays, MaxRetentionDays, and ChangeableForDays")
                do_response = backup_client.put_backup_vault_lock_configuration(
                    BackupVaultName=BackupVaultName,
                    MinRetentionDays=MinRetentionDays,
                    MaxRetentionDays=MaxRetentionDays,
                    ChangeableForDays=ChangeableForDays
                )
            except Exception as e:
                print("Error, min, max, and changeable not found, continuing", e)
                pass
    
    
    except Exception as e:
        print('Error in update_vault_lock()-',e)
        error = {}
        error['Error'] = 'Error in update_vault_lock'
        error['Cause'] = str(e)
        send_task_failure(taskToken, error['Error'], error['Cause'])


def delete_vault_lock(BackupVaultName, taskToken):
    try:
        print("entering delete_vault_lock")
        response = backup_client.delete_backup_vault_lock_configuration(
            BackupVaultName=BackupVaultName
        )

    except Exception as e:
        print('Error in delete_vault_lock()-',e)
        error = {}
        error['Error'] = 'Error in delete_vault_lock'
        error['Cause'] = str(e)
        send_task_failure(taskToken, error['Error'], error['Cause'])

def prepare_vault_lock_config(lock_config_on_vault, lock_config_in_db):
    try:
        print("starting prepare_vault_lock_config")
        print("lock_config_on_vault is ", lock_config_on_vault)
        print("lock_config_in_db is ", lock_config_in_db)
           
        config_to_apply = {}

        # 1. if all lock attributes in the db contain '36499', check if lock on vault exists, and return "Delete" (to delete the lock) or {} (do nothing if no lock exists)

        db_dummy = True
        for db_value in lock_config_in_db.values():
            if db_value != '36499':
                db_dummy = False
        if db_dummy and not lock_config_on_vault['VaultLocked']:
            print("all db attributes are dummy and no lock exists, nothing to do")
            return config_to_apply  # return an empty dictionary indicating nothing to do
        elif db_dummy and lock_config_on_vault['VaultLocked']:
            print("must delete the lock")
            config_to_apply['Delete'] = 'Delete'
            return config_to_apply
        else:
            print("DB contains values to process, continuing")

        # 2. if lock attributes in the db contain non-dummy value and corresponding vault value is not the same, then return the values to apply, else return {} (do nothing)

        for db_key, db_value in lock_config_in_db.items():
            if db_value != '36499':
                if db_key not in lock_config_on_vault:
                    print("vault value does not exist, storing db value")
                    config_to_apply[db_key] = db_value
                else:
                    print("checking value in vault against value in db")
                    if db_value != lock_config_on_vault[db_key]: # vault has a different value than in db, so return the db value
                        config_to_apply[db_key] = db_value
                    elif db_value == lock_config_on_vault[db_key]:
                        print("non dummy value in db is the same as the value on the vault, do nothing")
            else:
                print("db value is dummy, do nothing")
        return config_to_apply


 
    except Exception as e:
        print('Error in prepare_vault_lock_config()-',e)
        error = {}
        error['Error'] = 'Error in prepare_vault_lock_config'
        error['Cause'] = str(e)
        send_task_failure(taskToken, error['Error'], error['Cause'])


def get_db_lock_config(get_db_item_response, taskToken):
    try:
        db_lock_config = {}
        db_lock_config['BackupVaultMinRetentionDays'] = get_db_item_response['Item']['BackupVaultMinRetentionDays']
        db_lock_config['BackupVaultMaxRetentionDays'] = get_db_item_response['Item']['BackupVaultMaxRetentionDays']
        db_lock_config['BackupVaultChangeableForDays'] = get_db_item_response['Item']['BackupVaultChangeableForDays']
        print("lock config in DB is ", db_lock_config)
        return db_lock_config
    
    except Exception as e:
        print('Error in get_db_lock_config()-',e)
        error = {}
        error['Error'] = 'Error in get_db_lock_config'
        error['Cause'] = str(e)
        send_task_failure(taskToken, error['Error'], error['Cause'])
    
    

def lambda_handler(event, context):
    
    print('Received Event:',event)
    taskToken = event['TaskToken']
    BackupVaultName = event['BackupVaultName']
    ParameterSetName = event['ParameterSetName']
    StateName = 'sm3-LockConfiguration'
    #error = {}
    #error['TableArn'] = tableArn
    print("inside sm3 - sm3-LockConfiguration lambda") 

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
        'Message': 'LockConfiguration - Fail'
    }

    try:
        print("validating ParameterSetName")
        TableName = 'FtMMBackupVaultParameterSet'
        get_db_item_response = get_db_item(TableName, 'ParameterSetName', ParameterSetName) 
        print("get_db_item_response is ", get_db_item_response)
        if get_db_item_response != 'Failed':
            BackupVaultArn = get_db_item_response['Item']['BackupVaultArn']
            print("calling lock_config_in_db in the lambda")
            lock_config_in_db = get_db_lock_config(get_db_item_response, taskToken)
            print("calling get_vault_lock_config in the lambda")
            lock_config_on_vault = get_vault_lock_config(BackupVaultName)
            actual_config_to_apply = prepare_vault_lock_config(lock_config_on_vault, lock_config_in_db)
            if 'Delete' in actual_config_to_apply:
                delete_vault_lock(BackupVaultName, taskToken)
            else:
                update_vault_lock(BackupVaultName, actual_config_to_apply, taskToken)

            # update the state machine for sm3
            send_task_success(taskToken, success_payload_json)
            #update the report table for sm3
            StateSuccessFail = 'SUCCESS'
            TableName = 'FtMMBackupVaultReport'
            StateDetail = 'Vault Updated' # remove if pass StateDetail back to handler
            create_report_item(TableName, BackupVaultName, StateName, ParameterSetName, StateSuccessFail, StateDetail)

        else:
            # Add Failure message to the report table for sm3
            StateSuccessFail = 'FAIL'
            StateDetail = 'No config to apply'
            TableName = 'FtMMBackupVaultReport'
            create_report_item(TableName, BackupVaultName, StateName, ParameterSetName, StateSuccessFail, StateDetail)
            # Abort make manage, no database values to check
            send_task_failure(taskToken, 'failed to retrieve DB item', 'failed to retrieve DB item')
            
    except Exception as e:
        print("Error-", e)
        #error['Error'] = 'Exception occured while performing sm2 BackupVaultTags state machine'
        raise
