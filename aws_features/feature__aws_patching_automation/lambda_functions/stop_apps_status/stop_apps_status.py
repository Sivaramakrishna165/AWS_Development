'''
This lambda is used to check the status of application stopping status.
'''

import boto3
import json
import sys
import os
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))

def PrintException():
    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    captureErr = "Line No. : " + str(lineno)  + " | ERROR: " + str(exc_obj)
    return captureErr

def read_ssm_parameter(ssm_parameter):
    try:
        ssm_client = boto3.client('ssm',config=config)
        ssmParameter = ssm_client.get_parameter(Name=ssm_parameter)
        stop_apps_status = ssmParameter['Parameter']['Value']
        return stop_apps_status
    except:
        print(PrintException())


def lambda_handler(event, context):
    Patching_Type= event['Patching_Type']
    if Patching_Type == 'Adhoc':
        ssm_parameter = str(os.environ['AdhocEnableAppsStopping']) #'/DXC/AdhocPatchingAutomation/Enable_Apps_Stopping'
    else:
        ssm_parameter = str(os.environ['EnableAppsStopping']) #'/DXC/PatchingAutomation/Enable_Apps_Stopping'
    stop_apps_status = read_ssm_parameter(ssm_parameter)
    event['Stop_Apps_Status'] = stop_apps_status
    print("Event : ",event)
    return event

if __name__ == "__main__":
    event1 = {
  "PatchInstallOn": "DEV-NOV_1_2021_13_30_4HRS_BY_AY",
  "S3_Bucket": "dxc",
  "S3_directory_name": "OCT_2021/ap-south-1/patchJobId_968e4f46-145e-11ec-963a-91da71649e83",
  "CommandId": "79abcb2d-7af1-46eb-95ff-fd47ba77b7ab",
  "Status": "pending",
  "app_action": "start"
}
    lambda_handler(event1, "") 


