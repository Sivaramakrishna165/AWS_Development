"""
This Lambda function is a part of feature__selfheal_foundation stepfuction.
This Script takes Input(payload) passed through SNS topic, and logs the required
the data in the DynamoDB Table.
Input(payload) to be passed:
cs
{
	"InstanceId":"<instance-id>","OldStateValue":"OK","NewStateValue":"ALARM",
	"EventDate":"2022-05-30T07:21:40.269Z","Event":"CrowdStrikeFalconAgentFailure",
	"IncidentPriority":"3","region":"eu-west-2"
}
cw
{
	"instanceId":"<instance-id>","logGroupName":"/var/log/messages or Default-Log-Group",
	"logStreamName":"<instance-id>","OldStateValue":"OK","NewStateValue":"ALARM",
	"EventDate":"2022-05-30T07:21:40.269Z","Event":"CloudWatchAgentLogFailure",
	"IncidentPriority":"3","region":"eu-west-2"
}
bf
{
	"InstanceId":"<instance-id>","VolumeIds":[<vol-id>"],"LatestBackup":"2022-08-21T12:13:29.864Z","EventDate":"2022-08-22T07:13:40.269Z",
	"Event":"BackupFailure","IncidentPriority":"3","region":"ap-southeast-1"
}
In dxcms_sh_sfn_self_heal_master_sfn,
On successful check, next state choice_to_trigger_diagnosis is called.
On FAILURE, next State dynamodb_logging_error and then Notify_failure.
"""


import json
import boto3
import os
import uuid
import time
import traceback
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))

dynamodb_resource = boto3.resource('dynamodb',config=config)
dynamodb_client =  boto3.client('dynamodb',config=config)
ec2_client = boto3.client('ec2',config=config)
#table_name = "EC2BackupSelfHeal"
table_name = os.environ['table_name']
region = os.environ['AWS_REGION']

def success_token(event,task_token):
    try:
        print("success_token() triggered.")
        sf = boto3.client('stepfunctions',config=config)
        sf_output = json.dumps(event)
        sf_response = sf.send_task_success(
            taskToken=task_token,
            output=str(sf_output)
        )
        print("success task token sent - ", sf_response)
        return sf_response
    except Exception as e:
        print("Error success_token() - ",e)
        print("not able to send task success token.")
        failure_token(task_token, str(e)[:200], traceback.format_exc())

def failure_token(taskToken, error, err_cause):
    try:
        print("failure_token() triggered.")
        if isinstance(err_cause, dict):
            cause = json.dumps(err_cause)
        else:
            cause = str(err_cause)
        sf = boto3.client('stepfunctions',config=config)
        sf_response = sf.send_task_failure(
            taskToken=taskToken,
            error = json.dumps(error),
            cause = cause
        )
        print('failure task token sent - ',sf_response)
    except Exception as e:
        print("Error failure_token() - ", e)
        print("not able to send failure task token")
        raise

def generate_uniqueId():
    error = False
    selfHealJobId = ""
    try:
        print("generate_uniqueId() triggered.")
        selfHealJobId = "selfHealJobId_" + str(uuid.uuid1())
    except Exception as e:
        print("Error generate_uniqueId() - ",e)
        error = traceback.format_exc()
    finally:
        return selfHealJobId, error

def read_incident_priority(usecase):
    error = False
    try:
        if (usecase == "BackupFailure"):
            feature_name = "SelfhealEc2BackupFailure"
        elif (usecase == "CloudWatchAgentLogFailure"):
            feature_name = "SelfhealCloudwatchAgentFailure"
        elif (usecase == "CrowdStrikeFalconAgentFailure"):
            feature_name = "SelfhealCrowdstrikeAgentFailure"
        elif (usecase == "EC2CloudWatchAlarms"):
            feature_name = "SelfhealEC2CloudWatchAlarms"
        elif (usecase == "LambdaAnomalyDetection"):
            feature_name = "SelfhealLambdaAnomalyDetection"
        elif (usecase == "Ec2NativeBackupFailure"):
            feature_name = "SelfhealEc2NativeBackupFailure"
        else:
            feature_name = "unknown_feature"
            raise Exception(f"Wrong Event passed in payload. There is no {usecase} usecase in SelfHeal.")

        account_definition_reponse = dynamodb_client.get_item(
            TableName='AccountFeatureDefinitions',
            Key={'Feature': {'S': feature_name}}
        )

        incident_priority =  account_definition_reponse['Item']['FeatureParams']['M']['pSnowIncidentPriority']['M']['Default']['S']
        print(f"Incident Priority is: {incident_priority}")

        if (incident_priority in ["1","2","3"]):
            pass
        else:
            print(f"Incident Priority '{incident_priority}' does not match expected values ('1','2' or '3'). Taking fallback value: '3'.")
            incident_priority = "3"

        return incident_priority, error

    except Exception as e:
        print("Error read_incident_priority() - ",e)
        if feature_name == "unknown_feature":
            error = e
            return "unknown", error
        else:
            print(f"Error reading dynamodb table 'AccountFeatureDefinitions' with key 'Feature':{feature_name}")
            print(f"Taking fallback incident priority = '3'.")
            incident_priority = "3"
            return incident_priority, error
    
def bf_put_data(event_dict, priority, AccountId, AccountName, expiry_date, uniqueID, instance_id):
    print("bf_put_data() called.")
    error = False
    try:
        instance_name = instance_details(instance_id)
        table = dynamodb_resource.Table(table_name)
        item_dict = {
            'Event': event_dict['Event'], 'AccountId': AccountId, 'AccountName': AccountName,
            'Region': region, 'CIName':'EC2_Instance', 'ImpactedResourceName': instance_name,
            'ImpactedResourceId': instance_id, 'Volume ID': str(event_dict['VolumeIds']),
            'Event Date': event_dict['EventDate'], 'selfHealJobId': uniqueID,
            'Priority': priority,'expiry_date': expiry_date
        }
        response = table.put_item(
            Item= item_dict
        )
    except Exception as e:
        print("Error bf_put_data() - ",e)
        print("Error during table.put_item")
        error = traceback.format_exc()
    finally:
        return error

def cw_cs_put_data(event_dict, priority, AccountId, AccountName, expiry_date, uniqueID, instance_id):
    print("cw_cs_put_data() called.")
    error = False
    try:
        instance_name = instance_details(instance_id)
        table = dynamodb_resource.Table(table_name)
        item_dict = {
            'Event': event_dict['Event'], 'AccountId': AccountId, 'AccountName': AccountName,
            'Region': region, 'CIName':'EC2_Instance', 'ImpactedResourceName': instance_name,
            'ImpactedResourceId': instance_id,'Event Date': event_dict['EventDate'], 
            'selfHealJobId': uniqueID, 'Priority': priority,'expiry_date': expiry_date
        }
        response = table.put_item(
            Item= item_dict
        )
    except Exception as e:
        print("Error cw_cs_put_data() - ",e)
        print("Error during table.put_item")
        error = traceback.format_exc()
    finally:
        return error
    
def cw_alarms_put_data(event_dict, priority, AccountId, AccountName, expiry_date, uniqueID, instance_id):
    print("cw_alarms_put_data() called.")
    error = False
    try:
        instance_name = instance_details(instance_id)
        table = dynamodb_resource.Table(table_name)
        item_dict = {
            'Event': event_dict['Event'], 'AccountId': AccountId, 'AccountName': AccountName,
            'Region': region, 'CIName':'EC2_Instance', 'ImpactedResourceName': instance_name,
            'ImpactedResourceId': instance_id,'Event Date': event_dict['EventDate'], 
            'selfHealJobId': uniqueID, 'Priority': priority,'expiry_date': expiry_date
        }
        response = table.put_item(
            Item= item_dict
        )
    except Exception as e:
        print("Error cw_alarms_put_data() - ",e)
        print("Error during table.put_item")
        error = traceback.format_exc()
    finally:
        return error
    
def nbf_put_data(event_dict, priority, AccountId, AccountName, expiry_date, uniqueID, instance_id):
    print("nbf_put_data() called.")
    error = False
    try:
        instance_name = instance_details(instance_id)
        table = dynamodb_resource.Table(table_name)
        item_dict = {
            'Event': event_dict['Event'], 'AccountId': AccountId, 'AccountName': AccountName,
            'Region': region, 'CIName':'EC2_Instance', 'ImpactedResourceName': instance_name,
            'ImpactedResourceId': instance_id,'Event Date': event_dict['EventDate'], 
            'selfHealJobId': uniqueID, 'Priority': priority,'expiry_date': expiry_date
        }
        response = table.put_item(
            Item= item_dict
        )
    except Exception as e:
        print("Error nbf_put_data() - ",e)
        print("Error during table.put_item")
        error = traceback.format_exc()
    finally:
        return error

def lad_alarms_put_data(event_dict, priority, AccountId, AccountName, expiry_date, uniqueID, resource_id):
    print("lad_alarms_put_data() called.")
    error = False
    try:
        table = dynamodb_resource.Table(table_name)
        item_dict = {
            'Event': event_dict['Event'], 'AccountId': AccountId, 'AccountName': AccountName,
            'Region': region, 'CIName':'LambdaAnomalyCloudWatchAlarm', 'ImpactedResourceName': resource_id,
            'ImpactedResourceId': resource_id,'Event Date': event_dict['EventDate'], 
            'selfHealJobId': uniqueID, 'Priority': priority,'expiry_date': expiry_date
        }
        response = table.put_item(
            Item= item_dict
        )
    except Exception as e:
        print("Error lad_alarms_put_data() - ",e)
        print("Error during table.put_item")
        error = traceback.format_exc()
    finally:
        return error

def instance_details(instance_id):
    try:
        print("instance_details() triggered.")
        response = ec2_client.describe_instances(
            InstanceIds=[
                instance_id,
            ],
        )
        instance_name = "-"
        if 'Tags' in response['Reservations'][0]['Instances'][0].keys():
            for item in response['Reservations'][0]['Instances'][0]['Tags']:
                        #print(instance['Instances'][0]['Tags'])
                        if item['Key'] == 'Name' and item['Value'] != '':
                            instance_name = item['Value']
        return instance_name
    except Exception as e:
        print("Error instance_details() - ",e)
        print(traceback.format_exc())
        return "-"

def lambda_handler(event, context):
    global task_token, resource_id, event_name, resource_type
    print("input recieved to this script - " + str(event))
    error = False
    task_token = event["token"]
    event = event["Payload"]
    if('lambda' in event):
        if(isinstance(event['lambda'],str)):
            event = json.loads(event['lambda'])
        else:
            event = event['lambda']
    
    event_name = event['Event']
    event1  = {}
    try:
        if (event_name in ["BackupFailure", "CloudWatchAgentLogFailure", "CrowdStrikeFalconAgentFailure", "EC2CloudWatchAlarms", "Ec2NativeBackupFailure"]):
            if('instanceId' in event):
                resource_id = event['instanceId']
            else:
                resource_id = event['InstanceId']
            resource_type = "AWS::EC2::Instance"
        elif (event_name in ["LambdaAnomalyDetection"]):
            resource_id = event["resource_id"]
            resource_type = "LambdaAnomalyCloudWatchAlarm"
        else:
            raise Exception("Error - wrong usecase passed. Wrong payload passed, check event value.")

        AccountId = boto3.client('sts',config=config).get_caller_identity().get('Account')
        try:
            AccountName = boto3.client('iam',config=config).list_account_aliases()['AccountAliases'][0]
        except:
            AccountName = ""
        
        expiry_date = int(time.time()) + 7776000
        priority, error = read_incident_priority(event_name)
        if error:
            raise Exception("Wrong payload.")
        uniqueID, error = generate_uniqueId()
        if error:
            raise Exception("Error while generating unique id.")
        
        if (event_name == "BackupFailure"):
            error = bf_put_data(event, priority, AccountId, AccountName, expiry_date, uniqueID, resource_id)
        elif (event_name in ["CloudWatchAgentLogFailure", "CrowdStrikeFalconAgentFailure"]):
            error = cw_cs_put_data(event, priority, AccountId, AccountName, expiry_date, uniqueID, resource_id)
        elif (event_name == "EC2CloudWatchAlarms"):
            error = cw_alarms_put_data(event, priority, AccountId, AccountName, expiry_date, uniqueID, resource_id)
            event1["InitialTriggerDetails"] = event["InitialTriggerDetails"]
        elif (event_name == "Ec2NativeBackupFailure"):
            error = nbf_put_data(event, priority, AccountId, AccountName, expiry_date, uniqueID, resource_id)
        elif (event_name == "LambdaAnomalyDetection"):
            error = lad_alarms_put_data(event, priority, AccountId, AccountName, expiry_date, uniqueID, resource_id)
            event1["AlarmName"] = event["AlarmName"]
            event1["NewStateReason"] = event["NewStateReason"]
        else:
            raise Exception("Wrong payload passed, check event value.")
        if error:
            raise Exception(f"Error while storing data in {table_name} dynamodb table with selfHealJobId {uniqueID}.")
        
        event1['resource_id'] = resource_id
        event1['resource_type'] = resource_type
        event1['incident_priority'] = priority
        event1['Event Date'] = event['EventDate']
        event1['Event'] = event_name
        event1['region'] = region
        event1['account_id'] = AccountId
        event1['selfHealJobId'] = uniqueID
        
        print(event1)
        return success_token(event1,task_token)
    except Exception as e:
        print("Error lambda_handler() - ",e)
        if not error:
            error = traceback.format_exc()
        return failure_token(task_token, str(e)[:200], error)