'''
This Lambda script is used to update the tag as _BY/_BN based on the status of backup
'''

import boto3
import sys,os
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))

def PrintException():
    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    captureErr = "Line No. : " + str(lineno)  + " | ERROR: " + str(exc_obj)
    return captureErr


def tag_on_instance(instanceId,updatedTag):
    try:
        client = boto3.client('ec2',region_name = region,config=config)
        response = client.create_tags(    
            Resources=[
                instanceId,
            ],
            Tags=[
                {
                    'Key': 'PatchInstallOn',
                    'Value': updatedTag
                },
            ]
        )
    except:
        print(PrintException())


def fetch_instance_ids(TagValues,Patching_Tag):
    try:
        ec2_client = boto3.client("ec2",region_name = region,config=config)
        instanceTags = (TagValues + "*")
        instance_ids = []
        response = ec2_client.describe_instances(
        Filters=[
            {
                'Name': 'tag:'+Patching_Tag,
                'Values': [
                    instanceTags,
                ]
            },
        ],
        )
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                instance_ids.append(instance["InstanceId"])
        return instance_ids
    except:
        print(PrintException())

def update_patch_tag_on_instnace(S3_Bucket,S3_directory_name,tagValue,Patching_tag):
    try:
        print("Appending _BY on PatchInstallOn tag to indicate that Backup is successful")
        instance_ids = fetch_instance_ids(tagValue,Patching_tag)
        client = boto3.client('ec2',region_name = region,config=config)
        updatedTag = tagValue + "_BY"
        for instance in instance_ids:
            response = client.create_tags(    
                Resources=[
                    instance,
                ],
                Tags=[
                    {
                        'Key': Patching_tag,
                        'Value': updatedTag
                    },
                ]
            )
        print("Updated PatchInstallOn tag on all applicable the instances")
    except:
        print(PrintException())


def lambda_handler(event,context):
    print(f"Event : {event}")
    global region
    patching_type = event['Patching_Type']
    if patching_type == 'Standard':
        patching_tag = "PatchInstallOn"
    else:
        patching_tag = "AdhocPatchInstallOn"
    region = event['region']
    S3_Bucket = event['S3_Bucket']
    S3_directory_name = event['S3_directory_name']
    tagValue = event['PatchInstallOn']
    update_patch_tag_on_instnace(S3_Bucket,S3_directory_name,tagValue,patching_tag)
    return event



        
# simple test cases
if __name__ == "__main__":
    event1 = {"PatchInstallOn": "DEV-NOV_2_2021_13_30_4HRS","S3_Bucket": "dxc","S3_directory_name": "OCT_2021/ap-south-1/patchJobId_968e4f46-145e-11ec-963a-91da71649e83","region":"ap-south-1"}   
    lambda_handler(event1, "")