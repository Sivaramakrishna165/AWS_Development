'''
This Lambda function is used to terminate the SSM command if it is running beyond the mentioned time limit
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
  
def lambda_handler(event,context): 
    bucket_name = event['S3_Bucket']
    directory_name = event['S3_directory_name']
    appAction = event['app_action']    
    tagValue = event['PatchInstallOn']    
    commandId = event['CommandId']
    region = event['region']
    ssm_client = boto3.client('ssm',region_name = region,config=config)
    try:
        response = ssm_client.cancel_command(CommandId=commandId)
    except:
        print(PrintException())
    
    jsonValues = {}
    jsonValues['PatchInstallOn'] = tagValue
    jsonValues['CommandId'] = commandId
    jsonValues['S3_Bucket'] = bucket_name
    jsonValues['S3_directory_name'] = directory_name
    jsonValues['app_action'] = appAction
    jsonValues['region'] = region
    print(jsonValues)
    return jsonValues
  

if __name__ == "__main__":
    event1 = {'PatchInstallOn': 'APR_25_2021_14_0_4HRS','Count': '10', 'CommandId':'6c7a2309-1b72-495f-a988-54fed97b91b8','S3_Bucket': 'dxc', 'S3_directory_name': 'APR_2021','app_action':'stop',"region":"ap-south-1"}
    lambda_handler(event1, "")