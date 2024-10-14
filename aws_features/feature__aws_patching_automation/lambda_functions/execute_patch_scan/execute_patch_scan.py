'''
This Lambda script is used to trigger the patch scanning as part of the pre-tasks activity.
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

#def execute_ssm_command(ssm_client,instanceId,opFileName):
def execute_ssm_command(Patching_tag,tagValue,bucket_name,directory_name,downtimeSeconds):
    try:
        print("Executing SSM Command and the tagvalue is : ",tagValue)
        # instanceTags = ("*" + tagValue + "*")
        ssm_client = boto3.client('ssm',config=config)
        parameters = {}
        parameters["Operation"] = ["Scan"]
        parameters["RebootOption"] = ["NoReboot"]
        #OutputS3KeyPrefix = "PATCHING/" + directory_name + "/Outputs/Patch_Scan_Output_" + tagValue
        # OutputS3KeyPrefix = patchScanOutputFolder + tagValue
        
        response = ssm_client.send_command(
            Targets=[{'Key':'tag:'+Patching_tag ,'Values':[tagValue]}],
            DocumentName="AWS-RunPatchBaseline",
            Parameters = parameters,
            #OutputS3Region=bucket_region,
            # OutputS3BucketName=bucket_name,
            TimeoutSeconds=downtimeSeconds,
            # OutputS3KeyPrefix= OutputS3KeyPrefix,
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

        #write_csv_file(opFileName,instanceId,"FAILED",err)



def call_update_dynamodb_lambda_fun(patchJob_ids,attribute_name,attribute_value):
    lambda_client = boto3.client('lambda',config=config)
    for i in range(len(patchJob_ids)):
        dynamo_event = {'patchJob_id': patchJob_ids,'attribute_name':'pre_patch_scan_status','attribute_value':'in-progress'}
        response = lambda_client.invoke(
            FunctionName='dxcms-pa-lam-update-dynamodb',
            Payload=json.dumps(dynamo_event)
        )


def lambda_handler(event,context):
    patching_type = event['Patching_Type']
    if patching_type == 'Standard':
        patching_tag = "PatchInstallOn"
    else:
        patching_tag = "AdhocPatchInstallOn"
    tagValue = event['PatchInstallOn']
    bucket_name = event['S3_Bucket']
    directory_name = event['S3_directory_name']
    S3_Folder_Name = event['S3_Folder_Name']
    region = event["region"]
    Patch_Phase = event['Patch_Phase']
    print("tagValue : ", tagValue)
    # "Patch_Phase": "post-patch"
    phase = event['Patch_Phase']
    # if phase == "pre-patch":
    #     patchScanOutputFolder = S3_Folder_Name + "/" + "PATCHING/" + directory_name + "/Outputs/Pre-PatchScan/Patch_Scan_Output_"
    #     File_prefix = "Pre_PatchScanReport"
    # elif phase == "post-patch":
    #     patchScanOutputFolder = S3_Folder_Name + "/" + "PATCHING/" + directory_name + "/Outputs/Post-PatchScan/Patch_Scan_Output_"
    #     File_prefix = "Post_PatchScanReport"
        
    downtimeHours = tagValue.split("_")[5]
    #downtimeHours = len(downtimeHours)
    downtimeHours = downtimeHours[:len(downtimeHours) - 3]
    print("Downtime Hours : ", downtimeHours)
    downtimeSeconds = int(downtimeHours) * 3600
    if phase == "post-patch":
        tagValue = tagValue + "_BY_AY"
    commandId = execute_ssm_command(patching_tag,tagValue,bucket_name,directory_name,downtimeSeconds)
    #convert total downtime hours into minutes and checks how many 15 minutes in downtime minutes to find out count for Iteration
    count = (int(downtimeHours) * 60)/15
    count = round(count)
    if int(count) == 0:
        count = int(count) + 1
    #waitSeconds = 15 * 60    # Standard Wait minutes is 15 minutes to check Patch Scan status. Converting minutes to seconds.
    waitSeconds = 1 * 30
    patchJob_id = directory_name.split('/')[2]
    print("Patch_Job_Id  : ",patchJob_id)
    # call_update_dynamodb_lambda_fun(patchJob_id)
    jsonValues = {}
    jsonValues['Patching_Type'] = patching_type
    jsonValues['PatchInstallOn'] = tagValue
    jsonValues['S3_Bucket'] = bucket_name
    jsonValues['S3_directory_name'] = directory_name
    jsonValues['CommandId'] = commandId
    jsonValues['Status'] = "pending"
    jsonValues['Count'] = count
    jsonValues['WaitSeconds'] = waitSeconds
    jsonValues['app_action'] = "start"
    # jsonValues['File_prefix'] = File_prefix
    jsonValues['Patch_Phase'] = Patch_Phase
    jsonValues['S3_Folder_Name'] = S3_Folder_Name
    jsonValues['region'] = region
    print(jsonValues)
    return jsonValues
    
if __name__ == "__main__":
    #event1 = {'PatchInstallOn': 'WIN_TEST-JAN_24_2022_13_30_4HRS', 
    # 'S3_Bucket': 'aws-patching-automation-bucket-second', 
    # 'S3_directory_name': 'JAN_2022/ap-south-1/patchJobId_64f8d533-7907-11ec-b672-13bef3e2bdba',
    # 'S3_Folder_Name': 'test'
    # 'Patch_Phase':"pre-patch"}
    event1 = {
    "PatchInstallOn": "DEV-JUL_25_2021_14_0_5HRS",
    "Patch_Phase": "pre-patch",
    "S3_Bucket": "dxc",
    "S3_directory_name": "JUL_2021/ap-south-1/patchJobId_9ed70582-c5bd-11eb-8b34-92ef5533228a",
    'S3_Folder_Name': 'Patching_Automation_Reports'
}
    lambda_handler(event1, "")

