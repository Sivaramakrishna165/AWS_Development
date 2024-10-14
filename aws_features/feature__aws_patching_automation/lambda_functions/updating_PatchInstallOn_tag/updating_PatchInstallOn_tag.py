'''
This Lambda script updates the PatchInstallOn tag on the all instance which is having PatchInstalltemp tag
sample input : {
                    "PatchInstallOn": "testing-JUN_7_2023_13_5_4HRS",
                    "S3_Bucket": "dxcms.patchingautomation.567529657087.us-west-1",
                    "S3_directory_name": "MAY_2023/us-west-1/patchJobId_7ec67b43-feae-11ed-b007-57d89e3b79a7",
                    "S3_Folder_Name": "patching_reports",
                    "region": "us-west-1"
                }
'''
import os
import boto3
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))

region = os.environ['AWS_REGION']

ec2_client = boto3.client('ec2',region_name = region,config=config)
    
def create_Patch_install_tag(PatchInstallValue,instance_id,patch_type,patch_temp):
    try:
        print('Updating the Patch Install tag')
        ec2_client.create_tags(
                    Resources=[
                        instance_id,
                    ],
                    Tags=[
                        {
                            'Key': patch_type,
                            'Value': PatchInstallValue
                        },
                    ]
                )
        print('Deleting the Patch Install tag')
        ec2_client.delete_tags(
                Resources=[
                    instance_id,
                ],
                Tags=[
                    {
                        'Key': patch_temp
                    },
                ]
            )
    except Exception as e:
        print("Error in create_Patch_install_tag() ",e)


def update_patchTags(PatchInstallOn_value,patch_type,patch_temp):
    try:
        print(PatchInstallOn_value)
        instanceTags = ("*" + PatchInstallOn_value + "*")
        instanceIds = []
        filters = [{'Name':"tag:"+patch_type, 'Values':instanceTags}]
        
        response = ec2_client.describe_instances(
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
        
        for id in instanceIds:
            response = ec2_client.describe_instances(
                InstanceIds=[
                    id,
                ]
            )
            
            for instance in response['Reservations']:
                for resource in instance['Instances']:
                    for tag in resource['Tags']:
                        if tag["Key"] == "PatchInstallTemp":
                            PatchInstallTempValue = tag["Value"]
                            print("Instance id is ",id," and the tag is ",PatchInstallTempValue)
                            create_Patch_install_tag(PatchInstallTempValue,id,patch_type,patch_temp)
         
    except Exception as e:
        print("Error in update_patchTags() ",e)
    
def lambda_handler(event, context):
    print('Received event is ',event)
    PatchInstallOn_value = event['PatchInstallOn']
    Patching_Type= event['Patching_Type']
    if Patching_Type == 'Adhoc':
        patch_type = 'AdhocPatchInstallOn'
        patch_temp = 'AdhocPatchInstallTemp'
    else:
        patch_type = 'PatchInstallOn'
        patch_temp = 'PatchInstallTemp'
    update_patchTags(PatchInstallOn_value,patch_type,patch_temp)

    return event
