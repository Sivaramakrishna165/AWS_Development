# Implemented via AWSPE- 5776
from pickletools import read_uint1
import boto3
from botocore.config import Config
from boto3.dynamodb.conditions import Key
from datetime import datetime
import os
import json

# The triggering event is the create or update to True of the EC2 instance tag dxc_make_manage
'''
Default event to test the Lambda 
        {
          "resources": ["arn:ec2/<instanceid>"],
          "detail": {
            "tags": {
              "dxc_make_manage": "true",
              "dxc_mm_params": {
                "ParameterSetName": "default",
                "os-name": "<os-name>",
                "os-arch": "<os-arch>"
              }
            }
          }
        }

'''
# 1. when event recieved, process the event
#   - verify dxc_make_manage tag value is True or true
#   - get instanceId from the ARN
#   - validate dxc_mm_params tag exists and pull the parameters and values from Value.
#   - set dxc_make_manage tag to "InProgress"
# 2. ensure "Default" ParameterSetName is created with default values for mm process (one time activity)
# 3. update DynamoDB
#     - if it is a custom name, check if it exists in the DB, use it, otherwise, exit mm
#     - if it is Default, then use it 
                #print("updating instance report table")
                #instance_report_json = get_instance_report_json(mm_instance, ParameterSetName)
                ## add to dynamoDB
                #add_items(ddb_tbl_hrd_ami_crt, instance_report_json)
# 4. pass instanceId and ParameterSetName to the first state machine (step 1)
# 5. cleanup cron event from CFT


config=Config(retries=dict(max_attempts=10,mode='standard'))
ddb = boto3.resource('dynamodb', config=config)
ec2_client = boto3.client('ec2', config = config)
ec2_resource = boto3.resource('ec2', config = config)
state_client = boto3.client('stepfunctions', config = config)

ddb_inst_info = os.environ['ddbInstInfoTableName']
ddb_inst_rep = os.environ['ddbInstRepTableName']
ddb_param_set = os.environ['ddbParamSetTableName']
ddb_inst_alarm = os.environ['ddbInstAlarmsTableName']
state_fun_arn = os.environ['StateFunArn']

# Load the AWSMS supported default alarms
f = open('default_awsms_alarms_windows.json') 
default_awsms_alarms_windows = json.load(f)

f = open('default_awsms_alarms_linux.json') 
default_awsms_alarms_linux = json.load(f)

def validate_event(event):
    result_json = {
        "InstanceID": "None",
        "ParameterSetName": "None",
        "os-name": "None",
        "os-arch": "None",
        "tags_valid": "False"
    }
    
    # Note: one event is created for each instance, even when the dxc_make_manage tag is created or updated on multiple instances at the same time 
    #    - so there is only one resource arn in the list, the arn of the instance with the updated tag
   
    InstanceIdArn = event['resources']
    print("InstanceIdArn is ", InstanceIdArn)
    instId = InstanceIdArn[0].split("/")[1]
    result_json['InstanceID'] = instId
    print("instId is ", instId)
    tags = event['detail']['tags']
    print("tags are ", tags)
    dxc_make_manage = tags['dxc_make_manage']
    print("dxc_make_manage is ", dxc_make_manage)

    if 'dxc_mm_params' in tags:
        try:
            dxc_mm_params = json.loads(tags['dxc_mm_params'])
            print("type of dxc_mm_params is ", type(dxc_mm_params))
            print("dxc_mm_params is ", dxc_mm_params)
            if 'ParameterSetName' in dxc_mm_params and 'os-name' in dxc_mm_params and 'os-arch' in dxc_mm_params:
                print("found all required dxc_mm_params")
                result_json['ParameterSetName'] = dxc_mm_params['ParameterSetName']
                result_json['os-name'] = dxc_mm_params['os-name'].strip().upper()
                result_json['os-arch'] = dxc_mm_params['os-arch']
                result_json['tags_valid'] = 'True'
            else:
                print("Error, one or more dxc_mm_params not found")
                result_json['tags_valid'] = 'Error, one or more dxc_mm_params not found'
        except Exception as e:
            result_json['tags_valid'] = e
            print("Error, dxc_mm_params does not contain valid JSON", e)
    else:
        print("Error, dxc_mm_params tag does not exist, cannot process this instance")
        result_json['tags_valid'] = 'Error, dxc_mm_params tag does not exist, cannot process this instance'

    return result_json

def check_db_entry_exists(tbl_name, item_name, item_value):
    result = False

    try:
        table = ddb.Table(tbl_name)
        get_item_response = table.get_item(Key={item_name: item_value})
        if get_item_response['Item'][item_name] == item_value:
            print('Item %s found' % item_name)
            return True
        else:
            print('Item %s not found' % item_name)
            return False
    except KeyError as e:
        print(str(e) + "KeyError exception in check_db_entry_exists")
        return False

# Gets the Instance Type for the given InstanceID
def get_instance_type(instance_id):    
    try:
        instance = ec2_resource.Instance(instance_id)
        return instance.platform_details
    except Exception as e:
        print('Error ',e)
        raise
    
def create_default_db_item(tbl_name):
    default_exists = check_db_entry_exists(tbl_name, 'ParameterSetName', 'Default')
    if not default_exists:
        default_db_json = {
            "ParameterSetName": "Default",
            "EbsVolumeBackupLevel": "2",
            "BackupSchedule": "Default",
            "RetentionPeriod": "30",
            "ApplyPatching": "true",
            "ApplyEndPointProtection": "true",
            "ApplyMonitoring": "true",
            "ApplyLogging": "true",
            "OS-CIS-Compliance": "True",
            "OSServiceLevel": "GOLD",
            "Patch Group": "Default",
            "Project" : "Default",
            "Owner" : "Default",
            "Application" : "Default",
            "Environment" : "Default",
            "Compliance" : "",
            "LeaseExpirationDate" :""
        }
        add_items(tbl_name, default_db_json)
    else:
        print("Item Default already created in  {}, nothing to do".format(tbl_name))

    
def create_instance_alarm_item(tbl_name, instanceId):
    item_exists = check_db_entry_exists(tbl_name, 'InstanceId', instanceId)
    default_alarms = default_awsms_alarms_windows if "windows" in get_instance_type(instanceId).lower() else default_awsms_alarms_linux
    if not item_exists:
        default_db_json = {
            "InstanceId": instanceId,
            "Alarms": default_alarms
        }
        add_items(tbl_name, default_db_json)
    else:
        print("Item Default already created in {}, nothing to do".format(tbl_name))


def create_instance_report_item(tbl_name, instanceId, ParameterSetName):
    currentDT = datetime.now()
    date_time = currentDT.strftime('%m-%d-%Y_%H%M%S')
    inst_rep_exists = check_db_entry_exists(tbl_name, 'InstanceId', instanceId)
    if not inst_rep_exists:
        ddb_item_json = {
            "InstanceId": instanceId,
            "ParameterSetName": ParameterSetName,
            "CreationTime": date_time,
            "ModifyTime": "",
            "StateName": "",
            "StateSuccessFail": "",
            "StateDetail": ""
        }
        add_items(tbl_name, ddb_item_json)
    else:
        print("InstanceId already added to InstanceReport table, nothing to do")

def create_instance_info_item(tbl_name, event_results_json):
    InstID = event_results_json['InstanceID']
    PSetName = event_results_json['ParameterSetName']
    OsName = event_results_json['os-name']
    OsArch = event_results_json['os-arch']
    inst_info_exists = check_db_entry_exists(tbl_name, 'InstanceId', InstID)
    if not inst_info_exists:
        inst_info_db_json = {
            "InstanceId": InstID,
            "ParameterSetName": PSetName,
            "os-name": OsName,
            "os-arch": OsArch
        }
        add_items(tbl_name, inst_info_db_json)
    else:
        print("InstanceInfo Item already created, nothing to do")

def call_state_machine(state_machine_input, state_fun_arn):
    try:
        state_start_response = state_client.start_execution(
        stateMachineArn=state_fun_arn,
        input=state_machine_input
        )
        print("state_start_response is ", state_start_response)
    except Exception as e:
        print(str(e) + " exception in call_state_machine") 

def add_items(tbl_name, obj_json):
    try:
        table = ddb.Table(tbl_name)
        print(obj_json)
        table.put_item(Item=obj_json)
        # print(response)
    except boto3.exceptions.botocore.client.ClientError as e:
        print("Error adding item: {}  - {}".format(obj_json, str(e)))
        raise


def update_tag(resource, key, value):
    try:
        update_tag_response = ec2_client.create_tags(
            Resources=[
                resource,
            ],
            Tags=[
                {
                    'Key': key,
                    'Value': value
                },
            ]
        )
        print("update_tag_response is ", update_tag_response)
    except Exception as e:
        print("Error in update_tag", e)


def lambda_handler(event, context):
    print('Received Event:',event)
    event_results_json = validate_event(event)
    InstID = event_results_json['InstanceID']
    if event_results_json['tags_valid'] == 'True':
        PSetName = event_results_json['ParameterSetName']
        print("event_results_json from handler is ", event_results_json)
        create_default_db_item(ddb_param_set)
        create_instance_report_item(ddb_inst_rep, InstID, PSetName)
        create_instance_info_item(ddb_inst_info, event_results_json)
        create_instance_alarm_item(ddb_inst_alarm, InstID)
        update_tag(InstID, 'dxc_make_manage', 'In Progress')
        
        # Prepare the input accepted by Step function
        input = {}
        input['InstanceId'] = InstID
        input['ParameterSetName'] = PSetName
        state_machine_input = json.dumps(input)
        call_state_machine(state_machine_input, state_fun_arn)
    else:
        error_message = event_results_json['tags_valid']
        print("Processing failed Due to INVALID TAGS : ", error_message)
        update_tag(InstID, 'dxc_make_manage', 'Fail')
