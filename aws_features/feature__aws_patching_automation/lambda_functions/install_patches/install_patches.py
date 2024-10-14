'''
This Lamdba script triggers the patching installation using SSM command by passing 
tag key/value and communicates to user if there is an error on particular instance using SNS
'''

import boto3,os
import time, sys, datetime
from datetime import datetime
import csv
import json
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))

        
def PrintException():
    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    captureErr = "Line No. : " + str(lineno)  + " | ERROR: " + str(exc_obj)
    return captureErr

#def execute_ssm_command(ssm_client,instanceId,opFileName):
def execute_ssm_command(tagValue,bucket_name,directory_name,downtimeSeconds,Patching_tag):
    try:
        ssm_client = boto3.client('ssm',region_name = region,config=config)
        parameters = {}
        #parameters["Operation"] = ["Scan"]
        parameters["Operation"] = ["Install"]
        parameters["RebootOption"] = ["NoReboot"]
        OutputS3KeyPrefix = S3_Folder_Name + "/" + "PATCHING/" + directory_name + "/Outputs/Install-Patch/Patch_Install_Output_" + tagValue    
        snsIAMRole = os.environ['snsIAMRole']
        #snsTopic = 'arn:aws:sns:ap-south-1:338395754338:DXC_SNS_PatchNotifyFailure'
        #snsIAMRole = 'arn:aws:iam::338395754338:role/DXC-Patching-30-DXCSNSRole-1NHFJRW7G1TY4'
        #snsIAMRole = 'arn:aws:iam::338395754338:role/runcommand-sns-role'
        patch_Job_id = directory_name.split('/')[2]
        response = ssm_client.send_command(
            Targets=[{'Key':'tag:'+Patching_tag,'Values':[tagValue]}],
            DocumentName="AWS-RunPatchBaseline",
            Parameters = parameters,
            #OutputS3Region=bucket_region,
            # OutputS3BucketName=bucket_name,
            TimeoutSeconds=downtimeSeconds,
            Comment='Patch Job ID :' + patch_Job_id ,
            # OutputS3KeyPrefix= OutputS3KeyPrefix,
            MaxConcurrency = '50%',
            MaxErrors= '100%',
            ServiceRoleArn = snsIAMRole,
            NotificationConfig = {
                        'NotificationArn': snsTopic,
                        'NotificationEvents': ['Failed','Cancelled', 'TimedOut'],
                        'NotificationType': 'Invocation' },
            CloudWatchOutputConfig={
                'CloudWatchOutputEnabled': True
            }
        )
        print(response)
        cmd_id = response['Command']['CommandId']
        cmd_status = response['Command']['Status']
        print("COMMAND ID IS : ",cmd_id)
        attribute_name = 'patch_command_id'
        attribute_value = cmd_id
        call_update_dynamodb_lambda_function(patch_Job_id,attribute_name,attribute_value)
        return cmd_id

    except:
        err = PrintException()
        print(err)
        return "ERROR"

        #write_csv_file(opFileName,instanceId,"FAILED",err)

def call_update_dynamodb_lambda_function(patchJob_id,attribute_name,attribute_value):
    lambda_client = boto3.client('lambda',config=config)
    dynamo_event = {'patchJob_id': patchJob_id,'attribute_name':attribute_name,'attribute_value':attribute_value}
    response = lambda_client.invoke(
        FunctionName='dxcms-pa-lam-update-dynamodb',
        Payload=json.dumps(dynamo_event)
    )

def get_aws_account_info():
    accoundId = ""
    try:
        sts = boto3.client("sts",config=config)
        accoundId = sts.get_caller_identity()["Account"]    
    except:
        print(PrintException())
        accoundId = ""
    return accoundId

def lambda_handler(event,context): 
    global S3_Folder_Name,region,snsTopic
    global patchJob_id
    Patching_Type = event['Patching_Type']
    tagValue = event['PatchInstallOn']
    bucket_name = event['S3_Bucket']
    directory_name = event['S3_directory_name']
    S3_Folder_Name = event['S3_Folder_Name']
    region = event['region']
    print("tagValue : ", tagValue)
    if Patching_Type == 'Standard':
        patching_tag = "PatchInstallOn"
    else:
        patching_tag = "AdhocPatchInstallOn"
    
    account_id = get_aws_account_info()
    snsTopic = "arn:aws:sns:" + region + ":" + account_id + ":dxcms_pa_sns_notify_patch_failure"

    tag_value = tagValue.split("-")[1]
    downtimeHours = tag_value.split("_")[5]
    print("downtimeHours : ",downtimeHours)
    #downtimeHours = len(downtimeHours)
    downtimeHours = downtimeHours[:len(downtimeHours) - 3]
    print("Downtime Hours : ", downtimeHours)
    downtimeSeconds = int(downtimeHours) * 3600
    commandId = execute_ssm_command(tagValue,bucket_name,directory_name,downtimeSeconds,patching_tag)
    #convert total downtime hours into minutes and checks how many 15 minutes in downtime minutes to find out count for Iteration
    downtimeHoursStr = str(downtimeHours)
    if "." in downtimeHoursStr:
        downtimeHoursInt = int(downtimeHoursStr.split(".")[0]) + 1
    else:
        downtimeHoursInt = int(downtimeHours)

    count = (downtimeHoursInt * 60)/15
    count = round(count)
    if int(count) == 0:
        count = int(count) + 1
    
    waitSeconds = 15 * 60    # Standard Wait minutes is 15 minutes to check Patch Scan status. Converting minutes to seconds.    
    patchJob_id = directory_name.split('/')[2]
    call_update_dynamodb_lambda_function(patchJob_id,attribute_name = 'patch_job_status',attribute_value='in-progress')
    jsonValues = {}
    jsonValues['Patching_Type'] = Patching_Type
    jsonValues['PatchInstallOn'] = tagValue
    jsonValues['S3_Bucket'] = bucket_name
    jsonValues['S3_directory_name'] = directory_name
    jsonValues['CommandId'] = commandId
    jsonValues['Status'] = "pending"
    jsonValues['Count'] = count
    jsonValues['WaitSeconds'] = waitSeconds
    jsonValues['app_action'] = "start"
    jsonValues['S3_Folder_Name'] = S3_Folder_Name
    jsonValues['region'] = region
    print(jsonValues)
    return jsonValues
    
if __name__ == "__main__":
    event1 = {'PatchInstallOn': 'DEV-JUL_25_2021_14_0_5HRS_BY_AY', 'S3_Bucket': 'dxc', 'S3_directory_name': 'JUN_2021','S3_Folder_Name': 'test'}
    lambda_handler(event1, "")

