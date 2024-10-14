'''
This Lambda script is used to trigger the patch scanning for the instances on the schedule phase.
'''

import boto3,os
import time, sys, datetime
from datetime import datetime
import csv
import json
import math
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))

        
def PrintException():
    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    captureErr = "Line No. : " + str(lineno)  + " | ERROR: " + str(exc_obj)
    return captureErr

def fetch_all_instance_ids(TagValues,Patchinstalltag,Temppatchinstalltag):
    try:
        ec2_client = boto3.client('ec2')
        instance_ids = []
        server_count = 0
        for TagValue in TagValues:
            response_patch = ec2_client.describe_instances(
                Filters=[
                    {
                        'Name': 'tag:'+Patchinstalltag,
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
                        'Name': 'tag:'+Temppatchinstalltag,
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



def fetch_instance_ids(TagValues,Patchinstalltag,Temppatchinstalltag):
    try:
        ec2_client = boto3.client('ec2',region_name = region,config=config)
        instance_ids = []
        # instanceTags = (TagValues + "*")
        response = ec2_client.describe_instances(
            Filters=[
                {
                    'Name': 'tag:'+Patchinstalltag,
                    'Values': TagValues
                },
            ]
        )
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                instance_ids.append(instance["InstanceId"])
        response = ec2_client.describe_instances(
            Filters=[
                {
                    'Name': 'tag:'+Temppatchinstalltag,
                    'Values': TagValues
                },
            ]
        )
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                instance_ids.append(instance["InstanceId"])
        server_count = len(instance_ids)
        print("server_count is :", server_count)
        return server_count
    except:
        print(PrintException())

#def execute_ssm_command(ssm_client,instanceId,opFileName):
def execute_ssm_command(tagValue,bucket_name,directory_name,timeOutSeconds):
    try:
        # instanceIds = fetch_all_instance_ids(tagValue)
        ssm_client = boto3.client('ssm',config=config)
        parameters = {}
        parameters["Operation"] = ["Scan"]
        parameters["RebootOption"] = ["NoReboot"]
        response = ssm_client.send_command(
            Targets=[{'Key':'tag:PatchScanSchedulePhase' ,'Values':['True',]}],
            DocumentName="AWS-RunPatchBaseline",
            Parameters = parameters,
            Comment = "Patching Automation-Schedule Phase",
            # OutputS3BucketName=bucket_name,
            TimeoutSeconds=timeOutSeconds,
            MaxConcurrency = '50%',
            MaxErrors= '100%',
        )
        print(response)

        cmd_id = response['Command']['CommandId']
        cmd_status = response['Command']['Status']
        print("COMMAND ID IS : ",cmd_id)
        return cmd_id

    except:
        err = PrintException()
        print(err)
        return "ERROR"

def delete_tag_value(Instance_ids):
    ec2_client = boto3.client('ec2')
    response = ec2_client.delete_tags(
        Resources=Instance_ids,
        Tags=[
            {
                'Key': 'PatchScanSchedulePhase',
                'Value': 'True'
            },
        ]
    )
    print("response for deletion of tags : ",response)

def fetch_instance_ids_tagvalue():
    try:
        ec2_client = boto3.client('ec2')
        instance_ids = []
        server_count = 0
        # for TagValue in TagValues:
        response = ec2_client.describe_instances(
            Filters=[
                {
                    'Name': 'tag:PatchScanSchedulePhase',
                    'Values': ["True",]
                },
            ]
        )
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                instance_ids.append(instance["InstanceId"])
                
        server_count = len(instance_ids)
        print("server_count is :", server_count)
        return instance_ids
    except:
        print(PrintException())

def lambda_handler(event,context): 
    global region
    TagName = event['TagName']
    tagValues = event['TagValues']
    bucket_name = event['S3_Bucket']
    directory_name = event['S3_directory_name']
    S3_Folder_Name = event['S3_Folder_Name']
    region = event["region"]
    print("tagValues : ", tagValues)
    if TagName == 'Downtime Window':
        patchinstalltag = "PatchInstallOn"
        temppatchinstalltag = "PatchInstallTemp"
    else:
        patchinstalltag = "AdhocPatchInstallOn"
        temppatchinstalltag = "AdhocPatchInstallTemp"
    total_server_count = fetch_instance_ids(tagValues,patchinstalltag,temppatchinstalltag)
    timeOutSeconds = total_server_count * 60 
    Instance_Ids = fetch_all_instance_ids(tagValues,patchinstalltag,temppatchinstalltag)
    # generate_tags(Instance_Ids)
    all_instance_ids = fetch_instance_ids_tagvalue()
    print("Instance ids having the tag -PatchScanSchedulePhase, value as -True : ",all_instance_ids)
    commandId = execute_ssm_command(tagValues,bucket_name,directory_name,timeOutSeconds)
    
    delete_tag_value(Instance_Ids)
    #convert total timeOutSeconds into minutes and checks how many 15 minutes in downtime minutes to find out count for Iteration
    downtimeMinutes = int(timeOutSeconds)/60
    count = downtimeMinutes/15
    
    count = math.ceil(count)
    waitSeconds = 15 * 60    # Standard Wait minutes is 15 minutes to check Patch Scan status. Converting minutes to seconds.
    event['Count'] = count
    event['Status'] = "pending"
    event['WaitSeconds'] = waitSeconds
    event['CommandId'] = commandId
    return event
    
if __name__ == "__main__":

    event1 = {
    "TagValues": [
            "WIN_TEST-JAN_24_2022_13_30_4HRS",
            "RHEL_TEST-FEB_7_2022_11_15_5HRS",
            "RHEL_TEST-JAN_19_2022_5_40_0HRS"
        ],
    "S3_Bucket": "dxc",
    "S3_directory_name": "JUL_2021/ap-south-1",
    'S3_Folder_Name': 'Patching_Automation_Reports',
    "File_prefix": "PatchServerList",
    "region": "ap-south-1"
}
    lambda_handler(event1, "")

