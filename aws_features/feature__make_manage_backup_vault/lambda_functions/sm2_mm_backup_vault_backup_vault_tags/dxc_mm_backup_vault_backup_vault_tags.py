
'''
Implemented via AWSPE-6578, updated in AWSPE-6593
The function is part of the StateMachineBackupVault
State Machine Step 2 (sm2) - BackupVaultTags
sample event
{
    'BackupVaultName': '', 
    'ParameterSetName': '', 
    'TaskToken': ''
}
The function receives the trigger from state machine 1 (sm1) Access Vault.
It checks for the BackupVaultTags property value in the FtMMBackupVaultParameterSet Dynamodb table for the desired ParameterSetName.
BackupVaultTags represents the desired state (all desired tags) of the vault, minus the AWS applied tags aws:cloudformation:<stack-name | stack-id | logical-id>
If not "Dummy",  then the tags provided in DynamoDB are verified against the tags on the vault
  - If different, 
    - a check is made to determine if tags have been added or deleted. 
    - the appropriate change will be applied to the tags on the vault.
  - If the same, then no changes will be applied to the tags on the vault.
If "Dummy" then no changes will be applied to the tags on the vault.
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


def get_vault_tags(VaultArn):
    try:
        print("retrieving list of vault tags")
        NextToken = '' # Initialize in case MaxResults greater than 123
        while(NextToken is not None):
            if NextToken is None or NextToken == '':
                list_tags_response = backup_client.list_tags(
                    ResourceArn=VaultArn
                )
            else:
                list_tags_response = backup_client.list_tags(
                    ResourceArn=VaultArn,
                    NextToken=NextToken,
                    MaxResults=123
                )
            NextToken = list_tags_response['NextToken'] if('NextToken' in list_tags_response) else None
        print("list_tags_response is ", list_tags_response)
        return list_tags_response['Tags']

    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            return 'TagsNotFound'
        else:
            ClientError_reason = e.response['Error']['Code']
            print("ClientError_reason is: ", ClientError_reason)
            error = {}
            #error['BackupVaultName'] = BackupVaultName
            error['Error'] = 'Error in get_vault_tags'
            error['Cause'] = ClientError_reason
            return error

    except Exception as e:
        print('Error in get_vault_tags()-',e)
        error = {}
        error['BackupVaultName'] = BackupVaultName
        error['Error'] = 'Error in get_vault_tags'
        error['Cause'] = str(e)
        return error


def set_vault_tags(BackupVaultTags, BackupVaultArn, taskToken):
    try:
        print("applying tags from the DB table FtMMBackupVaultParameterSet to the backup vault")
        dbTags = json.loads(BackupVaultTags)

        tag_resource_response = backup_client.tag_resource(
            ResourceArn=BackupVaultArn,
            Tags=dbTags
        )

        print("tag_resource_response in set_vault_tags is ", tag_resource_response)
        return tag_resource_response

    except Exception as e:
        print('Error in set_vault_tags()-',e)
        error = {}
        error['BackupVaultTags'] = 'BackupVaultTags'
        error['Error'] = 'Error in set_vault_tags'
        error['Cause'] = str(e)
        send_task_failure(taskToken, error['Error'], error['Cause'])


def delete_vault_tags(taglist_to_delete, BackupVaultArn, taskToken):
    try:
        print("deleting tags from the backup vault according to the DB table FtMMBackupVaultParameterSet")
        #dbTags = json.loads(BackupVaultTags)
        #A list of keys to identify which key-value tags to remove from a resource.

        untag_resource_response = backup_client.untag_resource(
            ResourceArn=BackupVaultArn,
            TagKeyList=taglist_to_delete
        )

        print("untag_resource_response in delete_vault_tags is ", untag_resource_response)
        return untag_resource_response

    except Exception as e:
        print('Error in delete_vault_tags()-',e)
        error = {}
        error['BackupVaultTags'] = 'BackupVaultTags'
        error['Error'] = 'Error in set_vault_tags'
        error['Cause'] = str(e)
        send_task_failure(taskToken, error['Error'], error['Cause'])


def check_for_deletion(tags_in_db_json, get_vault_tags_response):
    try:
        return_dict = {"CallType": None, "DeleteList": None}
        if len(tags_in_db_json) < len(get_vault_tags_response):
            db_key_list = list(tags_in_db_json.keys())
            print("db_key_list is ", db_key_list)
            vault_key_list = list(get_vault_tags_response.keys())
            print("vault_key_list is ", vault_key_list)
            delete_key_list = list(set(vault_key_list) - set(db_key_list))
            print("delete_key_list is ", delete_key_list)
            print("type of delete_key_list is ", type(delete_key_list))
            return_dict['CallType'] = 'CallDelete'
            return_dict['DeleteList'] = delete_key_list
            print("return_dict is ", return_dict)
            return return_dict
        else:
            print("call set")
            return_dict['CallType'] = 'CallSet'
            print("return_dict is ", return_dict)
            return return_dict

    except Exception as e:
        print('Error in check_for_deletion()-',e)
        error = {}
        error['BackupVaultTags'] = 'BackupVaultTags'
        error['Error'] = 'Error in check_for_deletion'
        error['Cause'] = str(e)
        send_task_failure(taskToken, error['Error'], error['Cause'])


def lambda_handler(event, context):
    
    print('Received Event:',event)
    taskToken = event['TaskToken']
    BackupVaultName = event['BackupVaultName']
    ParameterSetName = event['ParameterSetName']
    StateName = 'sm2-BackupVaultTags'
    #error = {}
    #error['TableArn'] = tableArn
    print("inside sm2 - BackupVaultTags lambda") 

    success_payload_json = {
        'BackupVaultName': BackupVaultName,
        'ParameterSetName': ParameterSetName,
        'TaskToken':taskToken,
        'Message': 'BackupVaultTags - Success'
    }

    fail_payload_json = {
        'BackupVaultName': BackupVaultName,
        'ParameterSetName': ParameterSetName,
        'TaskToken':taskToken,
        'Message': 'BackupVaultTags - Fail'
    }

    try:
        print("validating ParameterSetName")
        TableName = 'FtMMBackupVaultParameterSet'
        get_db_item_response = get_db_item(TableName, 'ParameterSetName', ParameterSetName) 
        print("get_db_item_response is ", get_db_item_response)
        if get_db_item_response != 'Failed':
            BackupVaultArn = get_db_item_response['Item']['BackupVaultArn']
            tags_in_db = get_db_item_response['Item']['BackupVaultTags']
            print("type of tags_in_db is ", type(tags_in_db))
            if tags_in_db == 'Dummy':
                # Write NoChange to the report table for this state (no tags to apply)
                print("BackupVaultTags in FtMMBackupVaultParameterSet table contains 'Dummy' default, no tags to apply")
                StateSuccessFail = 'SUCCESS'
                StateDetail = 'No tags to apply'
                TableName = 'FtMMBackupVaultReport'
                create_report_item(TableName, BackupVaultName, StateName, ParameterSetName, StateSuccessFail, StateDetail)
                # call the next state machine
                send_task_success(taskToken, success_payload_json)
                    
            else:
                # apply the tags from the db onto the vault if the tags on the vault do not match the tags in the db 
                print("calling get_vault_tags in the lambda")
                get_vault_tags_response = get_vault_tags(BackupVaultArn)
                #print("type of get_vault_tags_response is ", type(get_vault_tags_response))
                print("get_vault_tags_response in lambda is ", get_vault_tags_response)
                if get_vault_tags_response == 'TagsNotFound':
                    # tags on vault do not exist, OK to apply tags
                    set_vault_tags_response = set_vault_tags(tags_in_db, BackupVaultArn, taskToken)
                    send_task_success(taskToken, success_payload_json)
                    #update the report table for sm2 (success or fail)
                    StateSuccessFail = 'SUCCESS'
                    StateDetail = 'Tags replaced'
                    TableName = 'FtMMBackupVaultReport'
                    create_report_item(TableName, BackupVaultName, StateName, ParameterSetName, StateSuccessFail, StateDetail)

                elif 'Error' in get_vault_tags_response:
                    print("Could not determine the tags on the vault, aborting")
                    send_task_failure(taskToken, get_vault_tags_response['Error'], get_vault_tags_response['Cause'])
                    
                else:
                    #print("type of get_vault_tags_response is ", type(get_vault_tags_response))
                    print("comparing vault tags to DB tags")
                    tags_in_db_json = json.loads(tags_in_db)
                    #get_vault_tags_response_json = json.loads(get_vault_tags_response)

                    delkeys = ['aws:cloudformation:logical-id', 'aws:cloudformation:stack-id', 'aws:cloudformation:stack-name']
                    for onekey in delkeys:
                        get_vault_tags_response.pop(onekey, None)

                    if tags_in_db_json == get_vault_tags_response:
                        PolicyMatch = True
                    else:
                        PolicyMatch = False
                    print("PolicyMatch is ", PolicyMatch)

                    if PolicyMatch:
                        # write NoChange to the report table for this state
                        StateSuccessFail = 'SUCCESS'
                        StateDetail = 'NoChange, vault tags match DB tags'
                        TableName = 'FtMMBackupVaultReport'
                        create_report_item(TableName, BackupVaultName, StateName, ParameterSetName, StateSuccessFail, StateDetail)
                        # Call the next state machine
                        send_task_success(taskToken, success_payload_json)
                    else:
                        check_for_deletion_response = check_for_deletion(tags_in_db_json, get_vault_tags_response)
                        if check_for_deletion_response['CallType'] == 'CallDelete':
                            print("calling delete tags")
                            delete_vault_tags(check_for_deletion_response['DeleteList'], BackupVaultArn, taskToken)
                            StateDetail = 'Requested tags deleted'
                        elif check_for_deletion_response['CallType'] == 'CallSet':
                            print("calling set_vault_tags to apply the tags from the DB to the backup vault")
                            set_vault_tags(tags_in_db, BackupVaultArn, taskToken)
                            StateDetail = 'New tags applied'
                        else:
                            send_task_failure(taskToken, 'improper response from check_for_deletion ', 'Bad CallType')
                        # update the state machine for sm2
                        send_task_success(taskToken, success_payload_json)
                        #update the report table for sm2
                        StateSuccessFail = 'SUCCESS'
                        TableName = 'FtMMBackupVaultReport'
                        create_report_item(TableName, BackupVaultName, StateName, ParameterSetName, StateSuccessFail, StateDetail)

        else:
            # Add Failure message to the report table for sm2
            StateSuccessFail = 'FAIL'
            StateDetail = 'No tags to apply'
            TableName = 'FtMMBackupVaultReport'
            create_report_item(TableName, BackupVaultName, StateName, ParameterSetName, StateSuccessFail, StateDetail)
            # Abort make manage, no database values to check
            send_task_failure(taskToken, 'failed to retrieve DB item', 'failed to retrieve DB item')

            
    except Exception as e:
        print("Error-", e)
        #error['Error'] = 'Exception occured while performing sm2 BackupVaultTags state machine'
        raise
