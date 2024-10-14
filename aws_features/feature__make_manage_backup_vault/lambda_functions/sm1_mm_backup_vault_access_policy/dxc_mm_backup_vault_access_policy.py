'''
Implemented via AWSPE-6578, updated in AWSPE-6593
The function is part of the StateMachineBackupVault
State Machine Step 1 (sm1) - Access Policy
sample event
{
    'BackupVaultName': '', 
    'ParameterSetName': '', 
    'TaskToken': ''
}
The function receives the trigger from the lambda processor.
It checks for the BackupVaultPolicy attribute in the FtMMBackupVaultParameterSet Dynamodb table.
If not "Dummy",  then the access policy provided in DynamoDB is verified against the policy on the vault
  - If different, the policy will be applied to the vault. 
  - If the same, then no changes will be applied to the vault
  - If 'Delete', then the existing policy on the vault will be deleted
If "Dummy" then no changes will be applied to the vault
Upon successful completion, a success token will be sent and the report table will be updated.
'''

from botocore.config import Config
from botocore.exceptions import ClientError
import boto3
from boto3.dynamodb.conditions import Key
from datetime import datetime
import os
import json

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


def get_vault_access_policy(BackupVaultName):
    try:
        print("in get_vault_access_policy")
        get_vault_policy_response = backup_client.get_backup_vault_access_policy(
            BackupVaultName=BackupVaultName
        )
        print("get_vault_policy_response in get_vault_access_policy is ", get_vault_policy_response)
        return get_vault_policy_response

    # fix the exception handling once the policy issues are resloved.
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            return 'PolicyNotFound'
        else:
            ClientError_reason = e.response['Error']['Code']
            print("ClientError_reason is: ", ClientError_reason)
            error = {}
            error['BackupVaultName'] = BackupVaultName
            error['Error'] = 'Error in get_vault_access_policy'
            error['Cause'] = ClientError_reason
            return error

    except Exception as e:
        print('Error in get_vault_access_policy()-',e)
        error = {}
        error['BackupVaultName'] = BackupVaultName
        error['Error'] = 'Error in get_vault_access_policy'
        error['Cause'] = str(e)
        return error


def apply_vault_policy(BackupVaultName, BackupVaultPolicy, taskToken):
    try:
        print("applying vault policy")
        put_policy_response = backup_client.put_backup_vault_access_policy(
            BackupVaultName=BackupVaultName,
            Policy=BackupVaultPolicy
        )

        print("put_policy_response in apply_vault_policy is ", put_policy_response)
        return put_policy_response

    except Exception as e:
        print('Error in apply_vault_policy()-',e)
        error = {}
        error['BackupVaultName'] = BackupVaultName
        error['Error'] = 'Error in apply_vault_policy'
        error['Cause'] = str(e)
        send_task_failure(taskToken, error['Error'], error['Cause'])


def delete_vault_policy(TableName, get_db_item_response, BackupVaultName, taskToken, ParameterSetName):
    # get vault policy
    
    try:
        get_vault_access_policy_response =  get_vault_access_policy(BackupVaultName)
        if ('PolicyNotFound' not in get_vault_access_policy_response) and ('Error' not in get_vault_access_policy_response):
            print("policy was found, ok to delete")
            delete_vault_policy_response = backup_client.delete_backup_vault_access_policy(
                BackupVaultName=BackupVaultName
            )
            print("setting BackupVaultPolicy in FtMMBackupVaultParameterSet back to default Dummy value")
            tbl_name = 'FtMMBackupVaultParameterSet'
            obj_json = get_db_item_response['Item']
            print("obj_json in delete_vault_policy is ", delete_vault_policy)
            obj_json['BackupVaultPolicy'] = 'Dummy'
            add_db_items_response = add_db_items(tbl_name, obj_json) 
            return 'SUCCESS'
        else:
            print("Policy not found, will not be deleted")

    except Exception as e:
        print('Error in delete_vault_policy()-',e)
        # send task failure
        error = {}
        error['BackupVaultName'] = BackupVaultName
        error['Error'] = 'Error in delete_vault_policy'
        error['Cause'] = str(e)
        send_task_failure(taskToken, error['Error'], error['Cause'])
        # Add Failure message to the report table for sm1
        StateSuccessFail = 'FAIL'
        StateDetail = 'Error getting vault access policy'
        TableName = 'FtMMBackupVaultReport'
        StateName = 'sm1-AccessPolicy'
        create_report_item(TableName, BackupVaultName, StateName, ParameterSetName, StateSuccessFail, StateDetail)

def lambda_handler(event, context):
    
    print('Received Event:',event)
    taskToken = event['TaskToken']
    BackupVaultName = event['BackupVaultName']
    ParameterSetName = event['ParameterSetName']
    StateName = 'sm1-AccessPolicy'
    #error = {}
    #error['TableArn'] = tableArn
    print("inside access policy sm1 lambda") 

    success_payload_json = {
        'BackupVaultName': BackupVaultName,
        'ParameterSetName': ParameterSetName,
        'TaskToken':taskToken,
        'Message': 'AccessPolicy - Success'
    }

    fail_payload_json = {
        'BackupVaultName': BackupVaultName,
        'ParameterSetName': ParameterSetName,
        'TaskToken':taskToken,
        'Message': 'AccessPolicy - Fail'
    }

    try:
        print("validating ParameterSetName")
        TableName = 'FtMMBackupVaultParameterSet'
        get_db_item_response = get_db_item(TableName, 'ParameterSetName', ParameterSetName) 
        print("get_db_item_response is ", get_db_item_response)
        if get_db_item_response != 'Failed':
            access_policy_in_db = get_db_item_response['Item']['BackupVaultPolicy']
            print("type of access_policy_in_db is ", type(access_policy_in_db))
            if access_policy_in_db == 'Dummy':
                # Write NoChange to the report table for this state (no policy to apply)
                StateSuccessFail = 'SUCCESS'
                StateDetail = 'No policy to apply'
                TableName = 'FtMMBackupVaultReport'
                create_report_item(TableName, BackupVaultName, StateName, ParameterSetName, StateSuccessFail, StateDetail)
                # call the next state machine
                send_task_success(taskToken, success_payload_json)
            elif access_policy_in_db == 'Delete':
                TableName = 'FtMMBackupVaultParameterSet'
                delete_vault_policy_response = delete_vault_policy(TableName, get_db_item_response, BackupVaultName, taskToken, ParameterSetName)
                if delete_vault_policy_response == 'SUCCESS':
                    # Write PolicyDeleted to the report table for this state (no policy to apply)
                    StateSuccessFail = 'SUCCESS'
                    StateDetail = 'PolicyDeleted'
                    TableName = 'FtMMBackupVaultReport'
                    create_report_item(TableName, BackupVaultName, StateName, ParameterSetName, StateSuccessFail, StateDetail)
                    # call the next state machine
                    send_task_success(taskToken, success_payload_json)
                else:
                    print("failure processing handled inside delete_vault_policy")    
                    
            else:
                # apply the policy from the db onto the vault if the policy on the vault does not match the policy in the db 
                # get_backup_vault_access_policy, meaning,  read the policy attached to the vault
                print("calling get_vault_access_policy in the lambda")
                get_vault_access_policy_response = get_vault_access_policy(BackupVaultName)
                print("get_vault_access_policy_response in lambda is ", get_vault_access_policy_response)
                if get_vault_access_policy_response == 'PolicyNotFound':
                    # policy on vault does does not exist, OK to apply policy
                    apply_vault_policy_response = apply_vault_policy(BackupVaultName, access_policy_in_db, taskToken)
                    send_task_success(taskToken, success_payload_json)
                    #update the report table for sm1 (success or fail)
                    StateSuccessFail = 'SUCCESS'
                    StateDetail = 'New Policy applied'
                    TableName = 'FtMMBackupVaultReport'
                    create_report_item(TableName, BackupVaultName, StateName, ParameterSetName, StateSuccessFail, StateDetail)

                elif 'Error' in get_vault_access_policy_response:
                    print("Could not determine the policy on the vault, aborting")
                    send_task_failure(taskToken, get_vault_access_policy_response['Error'], get_vault_access_policy_response['Cause'])
                    
                else:
                    policy_on_vault = get_vault_access_policy_response['Policy'] 
                    print("policy_on_vault is ", policy_on_vault)
                    print("type of policy_on_vault is ", type(policy_on_vault))
                    print("comparing vault policy to DB policy")

                    # if DB policy == vault policy

                    access_policy_in_db_json = json.loads(access_policy_in_db)
                    policy_on_vault_json = json.loads(policy_on_vault)
                    if access_policy_in_db_json == policy_on_vault_json:
                        PolicyMatch = True
                    else:
                        PolicyMatch = False
                    print("PolicyMatch is ", PolicyMatch)

                    if PolicyMatch:
                        # write NoChange to the report table for this state
                        StateSuccessFail = 'SUCCESS'
                        StateDetail = 'NoChange, vault policy matches DB policy'
                        TableName = 'FtMMBackupVaultReport'
                        create_report_item(TableName, BackupVaultName, StateName, ParameterSetName, StateSuccessFail, StateDetail)
                        # Call the next state machine
                        send_task_success(taskToken, success_payload_json)
                    else:
                        print("calling apply_vault_policy to apply the policy from the DB to the backup vault")
                        # update the report table for sm1 (success or fail)
                        apply_vault_policy_response = apply_vault_policy(BackupVaultName, access_policy_in_db, taskToken)
                        send_task_success(taskToken, success_payload_json)
                        #update the report table for sm1 (success or fail)
                        StateSuccessFail = 'SUCCESS'
                        StateDetail = 'New Policy applied'
                        TableName = 'FtMMBackupVaultReport'
                        create_report_item(TableName, BackupVaultName, StateName, ParameterSetName, StateSuccessFail, StateDetail)

        else:
            # Add Failure message to the report table for sm1
            StateSuccessFail = 'FAIL'
            StateDetail = 'No policy to apply'
            TableName = 'FtMMBackupVaultReport'
            create_report_item(TableName, BackupVaultName, StateName, ParameterSetName, StateSuccessFail, StateDetail)
            # Abort make manage, no database values to check
            send_task_failure(taskToken, 'failed to retrieve DB item', 'failed to retrieve DB item')



        #send task success to Task Token

            
    except Exception as e:
        print("Error-", e)
        #error['Error'] = 'Exception occured while performing Access Policy state machine'
        raise
