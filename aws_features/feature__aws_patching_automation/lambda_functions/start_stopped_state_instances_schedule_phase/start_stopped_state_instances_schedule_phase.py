'''
This Lambda script is used to start the stopped instances at the schedule phase to perform patch scanning
'''

import boto3
import json,sys
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))

def PrintException():
    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    captureErr = "Line No. : " + str(lineno)  + " | ERROR: " + str(exc_obj)
    return captureErr


def update_item_dynamoDB(patchJob_id,stoppedStateInstances):
    try:
        dynamodb = boto3.resource('dynamodb')
        dataItem = {}
              
        patch_table = dynamodb.Table('Ft_dxcms_patching_e2e_automation')        
        patch_table.update_item(
                Key={'patchJob_id': patchJob_id},
                UpdateExpression="set stopped_state_instances=:d",
                ExpressionAttributeValues={':d': stoppedStateInstances},
                ReturnValues="UPDATED_NEW"
                ) 
    except:
        print(PrintException())
        
def get_stopped_instances(tagValue):
    ec2_client = boto3.client('ec2',region_name = region,config=config)
    alarm_client = boto3.client('cloudwatch',config=config)
    instancelist = []
    instanceIPs = []
    alarms_to_disable = []
    ec2_filter = [
        {
            'Name': 'instance-state-name',
            'Values': ['stopped']
        },
        {
            'Name':"tag:PatchInstallOn",
            'Values':tagValue
        } 
    ]
    print(
        f'StartInstances: Searching for instances that match ec2_filter: {ec2_filter}')
    response_patch = ec2_client.describe_instances(Filters=ec2_filter)
    
    for r in response_patch['Reservations']:
        for instance in r['Instances']:
            instancelist.append(instance['InstanceId'])
    ec2_filter = [
        {
            'Name': 'instance-state-name',
            'Values': ['stopped']
        },
        {
            'Name':"tag:PatchInstallTemp",
            'Values':tagValue
        } 
    ]
    print(
        f'StartInstances: Searching for instances that match ec2_filter: {ec2_filter}')
    response_temp = ec2_client.describe_instances(Filters=ec2_filter)
    
    for r in response_temp['Reservations']:
        for instance in r['Instances']:
            instancelist.append(instance['InstanceId'])
    
    if instancelist:
        print("Stopped State Instances are : ", instancelist)
        return instancelist
    else:
        print("No instances are in Stopped State")
        return instancelist

def start_instances(ec2_instance_ids):
    try:
        ec2_client = boto3.client('ec2',region_name = region,config=config)    
        response = ec2_client.start_instances( InstanceIds=ec2_instance_ids)
    except:
        print(PrintException())

def fetch_all_instance_ids(TagValues,patchinstalltag,temppatchinstalltag):
    try:
        ec2_client = boto3.client('ec2')
        instance_ids = []
        server_count = 0
        for TagValue in TagValues:
            response_patch = ec2_client.describe_instances(
                Filters=[
                    {
                        'Name': 'tag:'+patchinstalltag,
                        'Values': [TagValue]
                    },
                ]
            )
            for reservation in response_patch['Reservations']:
                for instance in reservation['Instances']:
                    instance_ids.append(instance["InstanceId"])

            response_temp = ec2_client.describe_instances(
                Filters=[
                    {
                        'Name': 'tag:'+temppatchinstalltag,
                        'Values': [TagValue]
                    },
                ]
            )
            for reservation in response_temp['Reservations']:
                for instance in reservation['Instances']:
                    instance_ids.append(instance["InstanceId"])
                    
        server_count = len(instance_ids)
        print("server_count is :", server_count)
        return instance_ids
    except:
        print(PrintException())

def generate_tags(instance_ids):
    print("create PatchScanSchedulePhase tag on Instances :", instance_ids)
    ec2_client = boto3.client('ec2')
    tags_response = ec2_client.create_tags(
        Resources=instance_ids,
        Tags=[
            {
                'Key': 'PatchScanSchedulePhase',
                'Value': 'True'
            },
        ]
    )
    print("Create tags on instances response : ",tags_response)
        
def lambda_handler(event, context):
    try:
        global tagValue,S3_Bucket,S3_directory_name,local_folder
        global patchInstallStatusOfInstances,region
        Tagname = event['TagName']
        if Tagname == 'Downtime Window':
            patchinstalltag = "PatchInstallOn"
            temppatchinstalltag = "PatchInstallTemp"
        else:
            patchinstalltag = "AdhocPatchInstallOn"
            temppatchinstalltag = "AdhocPatchInstallTemp"
        tagValues = event['TagValues']
        S3_Bucket = event['S3_Bucket']
        S3_directory_name = event['S3_directory_name']
        
        patchMonth = S3_directory_name.split("/")[0]
        region = event['region']
        #patchJob_id = S3_directory_name.split("/")[2]
        
        # create tag on instances to perform the scan operation.
        Instance_ids = fetch_all_instance_ids(tagValues,patchinstalltag,temppatchinstalltag)
        generate_tags(Instance_ids)
        
        stoppedStateInstances = get_stopped_instances(tagValues)
        print(f"stoppedStateInstances = {stoppedStateInstances}")
        update_item_dynamoDB(region,stoppedStateInstances)
        update_item_dynamoDB(region,stoppedStateInstances)
        if stoppedStateInstances == None or stoppedStateInstances == "" or stoppedStateInstances == []:
            print("There is no Stopped Instances...")
        else:
            start_instances(stoppedStateInstances)
        
        
        return event
    except:
        print(PrintException())

if __name__ == "__main__":
    event1 =  {"TagValues": ["WIN_TEST-JAN_24_2022_13_30_4HRS","RHEL_TEST-FEB_7_2022_11_15_5HRS"],"S3_Bucket": "dxc","S3_directory_name": "JUN_2021/ap-south-1/patchJobId_98d80322-c0a9-11eb-b95e-5f544c2b0dea","region":"ap-south-1"}   
    lambda_handler(event1, "")     
