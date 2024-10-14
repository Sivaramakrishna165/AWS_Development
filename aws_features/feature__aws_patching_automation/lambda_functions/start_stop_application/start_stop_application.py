'''
This Lambda script is used to trigger the local script to stop/start the application

Sample inputs:
{
  "Patching_Type": "Adhoc",
  "PatchInstallOn": "PKT-JUL_16_2023_4_0_4HRS_BY",
  "S3_Bucket": "dxcms.patchingautomation.567529657087.ap-southeast-2",
  "S3_directory_name": "JUL_2023/ap-southeast-2/patchJobId_c58d56ca-2096-11ee-b087-db6d19ab9424",
  "app_action": "stop",
  "S3_Folder_Name": "patching_reports",
  "region": "ap-southeast-2",
  "Stop_Apps_Status": "ON"
}
'''

import boto3
import time, sys, datetime
from datetime import datetime
import csv
import json,os
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))
startapp=os.environ['startapp']
stopapp=os.environ['stopapp']
      
def PrintException():
    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    captureErr = "Line No. : " + str(lineno)  + " | ERROR: " + str(exc_obj)
    return captureErr
    
'''
def write_csv_file(opFileName,instanceId,result,output):
    with open(opFileName, 'a', newline='') as csvfile:
                filewriter = csv.writer(csvfile, delimiter=',')
                
                filewriter.writerow([instanceId, result, output ])
'''

def call_update_dynamodb_lambda_function(patchJob_id,attribute_name,attribute_value):
    lambda_client = boto3.client('lambda',config=config)
    dynamo_event = {'patchJob_id': patchJob_id,'attribute_name':attribute_name,'attribute_value':attribute_value}
    response = lambda_client.invoke(
        FunctionName='dxcms-pa-lam-update-dynamodb',
        Payload=json.dumps(dynamo_event)
    )


def execute_ssm_command(tagKey,tagValue,bucket_name,OutputS3KeyPrefix,ssmRunDocumentCmd,timeOutSeconds):
    try:
        print("TimeOut Seconds : ", timeOutSeconds)
        ssm_client = boto3.client('ssm',region_name = region,config=config)
        
        # snsTopic = os.environ['SnsTopic']
        # snsIAMRole = os.environ['SnsIamRole']    
        response = ssm_client.send_command(
            # Targets=[{'Key':tagKey ,'Values':[tagValue]}],
            Targets=[{'Key':'InstanceIds' ,'Values':instancelist}],
            DocumentName=ssmRunDocumentCmd,
            #OutputS3Region=bucket_region,
            OutputS3BucketName=bucket_name,
            TimeoutSeconds=timeOutSeconds,
            OutputS3KeyPrefix= OutputS3KeyPrefix,
            # MaxConcurrency = '50%',
            MaxErrors= '100%'
            )
        
        cmd_id = response['Command']['CommandId']
        cmd_status = response['Command']['Status']
        print("COMMAND ID IS : ",cmd_id)
        return cmd_id
    except:
        err = PrintException()
        print(err)  

        #write_csv_file(opFileName,instanceId,"FAILED",err)

def lambda_handler(event,context): 
    global S3_Folder_Name,region
    region = event['region']
    #make clients and resources from session
    ec2_client = boto3.client('ec2',region_name = region,config=config)
    ssm_client = boto3.client('ssm',region_name = region,config=config)
    global instancelist
    instancelist = []
    tagValue = event['PatchInstallOn']
    appAction = event['app_action']
    S3_Folder_Name = event['S3_Folder_Name']
    Patching_Type= event['Patching_Type']
    if Patching_Type == 'Adhoc':
        patch_type = 'AdhocPatchInstallOn'
    else:
        patch_type = 'PatchInstallOn'
    tagKey = "tag:" + patch_type
    timeOutMinutes = 1
    
    bucket_name = event['S3_Bucket']
    directory_name = event['S3_directory_name']
    
    ec2_filter = [
                {'Name':tagKey, 'Values':[tagValue]}        
                ]
    response = ec2_client.describe_instances(Filters=ec2_filter)
    for r in response['Reservations']:
        for instance in r['Instances']:
            instancelist.append(instance['InstanceId'])

    if instancelist:
        print(f'Found Instances that match ec2_filter: {ec2_filter}')
        print(instancelist)
    else:
        print(f'No Instances found that match ec2_filter: {ec2_filter}')
    
    for instanceId in instancelist:
        timeOutMinutes = timeOutMinutes + 1
        
    timeOutSeconds = int(timeOutMinutes) * 60 
    if appAction == "stop":
        ssmRunDocumentCmd = stopapp
        OutputS3KeyPrefix =  S3_Folder_Name +"/PATCHING/" + directory_name + "/AppDBStartStopStatus" + "/APPS_STOP_" + tagValue
        commandId = execute_ssm_command(tagKey,tagValue,bucket_name,OutputS3KeyPrefix,ssmRunDocumentCmd,timeOutSeconds)
        patchJob_id = directory_name.split('/')[2]
        call_update_dynamodb_lambda_function(patchJob_id,attribute_name = 'app_status',attribute_value='stopping-in-progress')
    elif appAction == "start":
        ssmRunDocumentCmd = startapp
        OutputS3KeyPrefix = S3_Folder_Name+ "/PATCHING/" + directory_name + "/AppDBStartStopStatus" + "/APPS_START_" + tagValue
        commandId = execute_ssm_command(tagKey,tagValue,bucket_name,OutputS3KeyPrefix,ssmRunDocumentCmd,timeOutSeconds)
        patchJob_id = directory_name.split('/')[2]
        call_update_dynamodb_lambda_function(patchJob_id,attribute_name='app_status',attribute_value='starting-in-progress')
    
    #Calucation here is, assuming one minute will be taken for starting/stopping application for each servers. hence, multiplying 1 (one minute) X no.of Instances
    #Finding out Count for iteration by checking how many 5 minutes in total timeOutSeconds.
    count = int(timeOutMinutes)/5 
    count = round(count)
    if int(count) == 0:
        count = int(count) + 1
    waitSeconds = 1 * 10    # Standard Wait minutes is 5 minutes to check Patch Scan status. Converting minutes to seconds.   
    jsonValues = {}
    jsonValues['Patching_Type'] = Patching_Type
    jsonValues['PatchInstallOn'] = tagValue
    jsonValues['CommandId'] = commandId
    jsonValues['Status'] = "pending"
    jsonValues['Count'] = count
    jsonValues['WaitSeconds'] = waitSeconds
    jsonValues['S3_Bucket'] = bucket_name
    jsonValues['S3_directory_name'] = directory_name
    jsonValues['app_action'] = appAction
    jsonValues['S3_Folder_Name'] = S3_Folder_Name
    jsonValues['region'] = region

    print(jsonValues)
    return jsonValues

if __name__ == "__main__":
    #event1 = {'PatchInstallOn': 'APR_25_2021_14_0_4HRS', 'S3_Bucket': 'dxc', 'S3_directory_name': 'APR_2021','app_action':'stop'}
    event1 = {
  "PatchInstallOn": "DEV-JUL_25_2021_14_0_5HRS_BY",
  "S3_Bucket": "dxc",
  "S3_directory_name": "JUL_2021/ap-south-1/patchJobId_7b69f86a-c86b-11eb-a4e3-32b48c8337c9",
  "app_action": "stop",
  "region":"ap-south-1"
}
    lambda_handler(event1, "")
