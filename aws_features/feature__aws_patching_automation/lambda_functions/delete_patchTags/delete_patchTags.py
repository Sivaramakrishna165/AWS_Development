'''
This Lambda script deletes the patch tag(PatchInstallOn) which is related to particular schedule as part of post patching activity.
'''

import re
import fnmatch
import boto3
import sys
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))

def PrintException():
    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    captureErr = "Line No. : " + str(lineno)  + " | ERROR: " + str(exc_obj)
    return captureErr

def fetch_instance_ids(TagValues,patch_type):
    # ec2 = boto3.resource('ec2',region_name=region)
    client = boto3.client('ec2',region_name=region,config=config)
    try:
        instanceIds = []
        instanceTags = ("*" + TagValues + "*")
        response = client.describe_instances(
            Filters=[
                {
                    'Name': 'tag:'+patch_type,
                    'Values': [
                         instanceTags,
                    ]
                },
            ]
            )    
        for r in response['Reservations']:
            for i in r['Instances']:
                instanceIds.append(i['InstanceId'])
        return instanceIds
    except:
        print(PrintException())

def lambda_handler(event,context):
    global region
    region = event['region']
    # ec2 = boto3.resource('ec2',region_name=region)
    client = boto3.client('ec2',region_name=region,config=config)
    global TagValues
    TagValues = event['PatchInstallOn']
    Patching_Type= event['Patching_Type']
    if Patching_Type == 'Adhoc':
        patch_type = 'AdhocPatchInstallOn'
    else:
        patch_type = 'PatchInstallOn'
    pattern = (TagValues + "*")
    InstanceIds = fetch_instance_ids(TagValues,patch_type)
    if InstanceIds == [] or InstanceIds == "" or InstanceIds == None:
        print(f"No Instance Id found with matching tag value : {TagValues} . Hence, skipping to further execution")
    else:
        print("Found Instances with PatchInstallOn Tag value and deleting them...")
        for i in range(len(InstanceIds)):
            response_1 = client.delete_tags(
                Resources=[
                    InstanceIds[i],
                ],
                Tags=[
                    {
                        'Key': patch_type
                    },
                ]
            )
            if Patching_Type == 'Adhoc':
                response_2 = client.delete_tags(
                Resources=[
                    InstanceIds[i],
                ],
                Tags=[
                    {
                        'Key': 'Adhoc Downtime Window'
                    },
                ]
            )
        print("Deleted PatchInstallOn tags on instances")
    return event


if __name__ == "__main__":
    #PatchInstallOnTagValues = ['APR_4_2021_14_30_4HRS', 'APR_11_2021_14_30_4HRS', 'APR_4_2021_03_30_4HRS', 'APR_18_2021_14_30_4HRS']
    event1 = {'PatchInstallOn': "MAY_9_2021_8_0_5HRS", 'S3_Bucket': 'dxc', 'S3_directory_name': 'APR_2021'}
    #event1 = {"TagValues": PatchInstallOnTagValues }

    lambda_handler(event1, "")






