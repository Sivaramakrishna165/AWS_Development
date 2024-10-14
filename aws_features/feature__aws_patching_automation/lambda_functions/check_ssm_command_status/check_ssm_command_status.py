'''
This Lambda script checks the status of SSM command ID which is triggered by another lambda.
'''

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

def wait_for_ssm_command(commandId):
    try:
        ssm_client = boto3.client('ssm',region_name = region,config=config)
        response = ssm_client.list_commands(CommandId=commandId)

        if response['Commands'][0]['Status'] in ('Success'):
            return "completed"
        elif response['Commands'][0]['Status'] in ('Cancelled', 'Failed', 'TimedOut'):
            #return "failed"
            return "completed"
        else:
            return "pending"
        print("RESULT : ",result)
    except:
        print(PrintException())
   
def lambda_handler(event,context): 
    try:
        global S3_Folder_Name,region
        region = event['region']
        patching_type = event['Patching_Type']
        if patching_type == 'Standard':
            patching_tag = "PatchInstallOn"
        else:
            patching_tag = "AdhocPatchInstallOn"
        bucket_name = event['S3_Bucket']
        directory_name = event['S3_directory_name']
        appAction = event['app_action']
        S3_Folder_Name = event['S3_Folder_Name']
        tagValue = event['PatchInstallOn']
        waitSeconds = event['WaitSeconds']
        
        commandId = event['CommandId']
        count = event['Count']
        count = int(count) - 1
        status = wait_for_ssm_command(commandId)
        jsonValues = {}
        jsonValues['Patching_Type'] = patching_type
        jsonValues['PatchInstallOn'] = tagValue
        jsonValues['Status'] = status
        jsonValues['Count'] = count
        jsonValues['WaitSeconds'] = waitSeconds
        jsonValues['CommandId'] = commandId
        jsonValues['S3_Bucket'] = bucket_name
        jsonValues['S3_directory_name'] = directory_name
        jsonValues['app_action'] = appAction
        jsonValues['S3_Folder_Name'] = S3_Folder_Name
        jsonValues['region'] = region
        print(jsonValues)
        return jsonValues
    except:
        print(PrintException())
  

if __name__ == "__main__":
    event1 = {'PatchInstallOn': 'APR_25_2021_14_0_4HRS','Count': '10', 'CommandId':'0bbf6a60-d25d-43fb-983f-49b758ff2d39','S3_Bucket': 'dxc', 'S3_directory_name': 'APR_2021','app_action':'stop','S3_Folder_Name': 'test',"region":"ap-south-1"}
    lambda_handler(event1, "")