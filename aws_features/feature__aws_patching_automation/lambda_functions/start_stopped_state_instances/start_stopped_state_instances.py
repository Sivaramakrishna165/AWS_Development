'''
This Lambda script is used to start the stopped instances to perform patch scanning
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
        
def get_stopped_instances(tagValue,Patching_tag):
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
            'Name':"tag:"+Patching_tag,
            'Values':[tagValue]
        } 
    ]
    print(
        f'StartInstances: Searching for instances that match ec2_filter: {ec2_filter}')
    response = ec2_client.describe_instances(Filters=ec2_filter)
    
    for r in response['Reservations']:
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
        
def lambda_handler(event, context):
    global tagValue,S3_Bucket,S3_directory_name,local_folder
    global patchInstallStatusOfInstances,region
    patching_type = event['Patching_Type']
    if patching_type == 'Standard':
        patching_tag = "PatchInstallOn"
    else:
        patching_tag = "AdhocPatchInstallOn"
    tagValue = event['PatchInstallOn']
    S3_Bucket = event['S3_Bucket']
    S3_directory_name = event['S3_directory_name']
    
    patchMonth = S3_directory_name.split("/")[0]
    region = event['region']
    patchJob_id = S3_directory_name.split("/")[2]

    client = boto3.client('ec2',config=config)
    response = client.describe_instances(
        Filters=[
            {
                'Name': 'tag:'+patching_tag,
                'Values': [
                        tagValue,
                ]
            },
        ]
        )    
    if response['Reservations'] == [] or response['Reservations'] == None or response['Reservations'] == "":
        sys.exit(f"ERROR : No Instances Id found with tag value {tagValue}")
    
    stoppedStateInstances = get_stopped_instances(tagValue,patching_tag)
    update_item_dynamoDB(patchJob_id,stoppedStateInstances)
    if stoppedStateInstances == None or stoppedStateInstances == "" or stoppedStateInstances == []:
        print("There is no Stopped Instances...")
    else:
        start_instances(stoppedStateInstances)
    
    return event


if __name__ == "__main__":
    event1 =  {"PatchInstallOn": "DEV-JUL_25_2021_14_0_5HRS","S3_Bucket": "dxc","S3_directory_name": "JUN_2021/ap-south-1/patchJobId_98d80322-c0a9-11eb-b95e-5f544c2b0dea","region":"ap-south-1"}   
    lambda_handler(event1, "")     
