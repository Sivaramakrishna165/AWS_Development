'''
#dxc_mm_backup_vault_lambda_processor.py
#Implemented via AWSPE-6578

# The trigger event is based on the create/update of the tag dxc_backupvault_make_manage to true/True/TRUE in the Dynamodb tables

# Once the event is received, the function will process the same.
# Extracts the tablearn and tablename from the event.
# Validate the dxc_backupvault_make_manage tag is TRUE/True/true on the backup vault
# Validate the dxc_backupvault_parameter_set tag is set on the backup vault, otherwise, an exception will be thrown.
#       FtMMBackupVaultParameterSet - Dynamo db table name containing the settings to be verified and applied to the vault.
#       FtMMBackupVaultReport - Dynamo db table containing a partition key and a sort key, used for maintaining make manage status
# Once the tables will be created and loaded with default values.  The values from the table will be applied, unless no changes required for defaults.

TBD: sample event:

{
   "resources":[""],
   "detail":{
      "tags":{
         "dxc_backupvault_make_manage":"TRUE/True/true"
         "dxc_backupvault_parameter_set" : "Default/<customer created custom value>"
      }
   }
}

'''

#from boto_helper import boto_helper
#boto_obj = boto_helper()
import boto3
from botocore.config import Config
from boto3.dynamodb.conditions import Key
from datetime import datetime
import os
import json

config=Config(retries=dict(max_attempts=10,mode='standard'))
ddb = boto3.resource('dynamodb', config=config)
state_client = boto3.client('stepfunctions', config = config)
backup_client = boto3.client('backup')


#ddb_info_table = os.environ['MMDdbInfoTableName']
#ddb_alarms_table = os.environ['MMDdbAlarmsTableName']
#ddb_rep_table = os.environ['MMDdbRepTableName']
state_fun_arn = os.environ['StateFunArn']
#dynamodb_log_group=os.environ['MMDdbLogGroupName']
#dynamodb_log_stream=os.environ['MMDdbLogStreamName']

#Load the MakeManage - Dynamodb default alarms
##f = open('default_ddb_table_alarms.json') 
##default_ddb_table_alarm = json.load(f)

# Be careful - each field in the item must be populated to prevent loss of the field.

 

def set_tag_inprogress(BackupVaultArn):
    try:
        print("setting vault tag to InProgress")
        target_tag = {}
        target_tag['dxc_backupvault_make_manage'] = 'InProgress'
        tag_resource_response = backup_client.tag_resource(
            ResourceArn=BackupVaultArn,
            Tags=target_tag
        )
    except Exception as e:
        print('Error:set_tag_inprogress()-', e)
        except_reason = "Exception error in set_tag_inprogress"

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


def add_items(tbl_name, obj_json):
    try:
        table = ddb.Table(tbl_name)
        print(obj_json)
        table.put_item(Item=obj_json)
        # print(response)
    except boto3.exceptions.botocore.client.ClientError as e:
        print("Error adding item: {}  - {}".format(obj_json, str(e)))
        raise

def check_db_entry_exists(tbl_name, partition_key, partition_value, sort_key=None, sort_value=None):
    #result = False
    table = ddb.Table(tbl_name)
    if sort_key == None:
        get_item_response = table.get_item(Key={partition_key: partition_value})
        print("get_item_response 1 in check_db_entry_exists is ", get_item_response)
        try:
            if get_item_response['Item'][partition_key] == partition_value:
                print("found the partition_key: ", partition_key)
                print("returning true")
                return True
        except KeyError as e:
            #print(str(e) + "Item does not exist, ok to create default item")
            print(str(e) + 'Item {} does not exist, ok to create default item'.format(partition_key))
            return False

    else:
        get_item_response = table.get_item(Key={partition_key: partition_value, sort_key: sort_value})
        print("get_item_response 2 in check_db_entry_exists is ", get_item_response)
        try:
            if get_item_response['Item'][partition_key] == partition_value:
                print("found the partition_key: ", partition_key)
                print("returning true")
                return True
        except KeyError as e:
            print(str(e) + 'Item {} does not exist, ok to create default item'.format(partition_key))
            return False


def create_default_db_items():
    ### Create defaults for FtMMBackupVaultParameterSet
    tbl_name = 'FtMMBackupVaultParameterSet'
    default_exists = check_db_entry_exists(tbl_name, 'ParameterSetName', 'Default')
    # The AttributeValue for a key attribute cannot contain an empty string value 
    if not default_exists:
        try:
            default_db_json = {
                "ParameterSetName": "Default",
                "BackupVaultPolicy": "Dummy",
                "BackupVaultMinRetentionDays": '30',
                "BackupVaultMaxRetentionDays": '36499',
                "BackupVaultChangeableForDays": '36499',
                "BackupVaultSNSTopicArn": "Dummy",
                "BackupVaultEvents": ["Dummy"],
                "BackupVaultArn": "Dummy",
                "BackupVaultTags": "Dummy"
            }
            add_items(tbl_name, default_db_json)
        except Exception as e:
            print("Error creating default item for FtMMBackupVaultParameterSet in create_default_db_items", e)
    else:
        print("Item Default already created in  {}, nothing to do".format(tbl_name))

    ### Create defaults for FtMMBackupVaultReport
    tbl_name = 'FtMMBackupVaultReport'
    default_exists = check_db_entry_exists(tbl_name, 'BackupVaultName', 'Default', 'StateName', 'Dummy')
    # The AttributeValue for a key attribute cannot contain an empty string value 
    if not default_exists:
        try:
            default_db_json = {
                "BackupVaultName": "Default",
                "CreationTime": "Dummy",
                "StateSuccessFail": "Dummy",
                "ParameterSetName": "Dummy", 
                "StateDetail": "Dummy",
                "StateName": "Dummy"
            }
            add_items(tbl_name, default_db_json)
        except Exception as e:
            print("Error creating default item for FtMMBackupVaultReport in create_default_db_items", e)
    else:
        print("Item Default already created in  {}, nothing to do".format(tbl_name))


#To validate the tags recevied from a backup vault.
def validate_event(event):
    result_json = {
        "BackupVaultArn": "None",
        "BackupVaultName": "None",
        "dxc_backupvault_make_manage": "None",
        "dxc_backupvault_parameter_set": "None",
        "tags_valid": "False"
    }
    
    # Note: one event is created for each backup vault, even when the dxc_backupvault_make_manage tag is created or updated on multiple vaults at the same time 
    #    - so there is only one resource arn in the list, the arn of the backup vault with the updated tag
    try: 
        BackupVaultArn = event['resources'][0]
        print("BackupVaultArn is ", BackupVaultArn)
        BackupVaultName = BackupVaultArn.split(":")[6]
        print("BackupVaultName is ", BackupVaultName)

        result_json['BackupVaultArn'] = BackupVaultArn
        result_json['BackupVaultName'] = BackupVaultName
        tags = event['detail']['tags']
        print("tags are ", tags)
        dxc_backupvault_make_manage = tags['dxc_backupvault_make_manage']
        #dxc_backupvault_parameter_set = tags['dxc_backupvault_parameter_set']
        if dxc_backupvault_make_manage in ["True", "true", "TRUE"] and 'dxc_backupvault_parameter_set' in tags:
            result_json['dxc_backupvault_make_manage'] = dxc_backupvault_make_manage
            result_json['dxc_backupvault_parameter_set'] = tags['dxc_backupvault_parameter_set']
            result_json['tags_valid'] = 'True'
        else:
            raise ValueError('Incorrect dxc_backupvault_make_manage tag value')
    except Exception as e:
        result_json['tags_valid'] = e
        print("Error in validate_event ", e)

    print("result_json in validate_event is ", result_json) 
    return result_json

def validate_db_parametersetname(BackupVaultName, ParameterSetName):
    try:
        BackupVaultParameterSet_Item = get_db_item('FtMMBackupVaultParameterSet', 'ParameterSetName', ParameterSetName)
        print("BackupVaultParameterSet_Item is ", BackupVaultParameterSet_Item)
        if BackupVaultParameterSet_Item['Item']['ParameterSetName'] == ParameterSetName:
            print('ParameterSetName {} from tag has been located in the ParameterSet database'.format(ParameterSetName))
            return True
        else:
            raise Exception('Error: ParameterSetName {} from the tag does not exist in the ParameterSet database, aborting make manage.'.format(ParameterSetName))
    except KeyError as e:
        print(str(e) + 'Error: ParameterSetName {} from the tag does not exist in the ParameterSet database, aborting make manage.'.format(ParameterSetName))
        # add call here to update the reports table to failure status

def call_state_machine(state_machine_input, state_fun_arn):
    try:
        state_start_response = state_client.start_execution(
        stateMachineArn=state_fun_arn,
        input=state_machine_input
        )
        print("state_start_response is ", state_start_response)
    except Exception as e:
        print(str(e) + " exception in call_state_machine")

def write_vault_arn(partition_value, BackupVaultArn):
    try:
        tbl_name = 'FtMMBackupVaultParameterSet'
        partition_key = 'ParameterSetName'
        get_db_item_response = get_db_item(tbl_name, partition_key, partition_value)
        dbItem = get_db_item_response['Item']
        dbItem['BackupVaultArn'] = BackupVaultArn
        print("dbItem in write_vault_arn is ", dbItem)
        add_item_response = add_items(tbl_name, dbItem)
    except Exception as e:
        print(str(e) + " exception in write_vault_arn")

    
def lambda_handler(event, context):
    print('Received Event:',event)
    event_results_json = validate_event(event)
    print("event_results_json from handler is ", event_results_json)
    if event_results_json['tags_valid'] == 'True':
        BackupVaultArn = event_results_json['BackupVaultArn']
        BackupVaultName = event_results_json['BackupVaultName']
        ParameterSetName = event_results_json['dxc_backupvault_parameter_set'] 

        write_vault_arn_response = write_vault_arn(ParameterSetName, BackupVaultArn)
        set_tag_inprogress_response = set_tag_inprogress(BackupVaultArn)
        create_default_db_items()
        valid_parameterset = validate_db_parametersetname(BackupVaultName, ParameterSetName)

        #create_instance_report_item(ddb_inst_rep, InstID, PSetName)
        #create_instance_info_item(ddb_inst_info, event_results_json)
        #create_instance_alarm_item(ddb_inst_alarm, InstID)
        #update_tag(InstID, 'dxc_make_manage', 'In Progress')
        #
        ## Prepare the input accepted by Step function
        if valid_parameterset:
            input = {}
            input['BackupVaultName'] = BackupVaultName
            input['ParameterSetName'] = ParameterSetName
            state_machine_input = json.dumps(input)
            call_state_machine(state_machine_input, state_fun_arn)
    else:
        error_message = event_results_json['tags_valid']
        print("Processing failed Due to INVALID TAGS : ", error_message)
        #update_tag(InstID, 'dxc_make_manage', 'Fail')
