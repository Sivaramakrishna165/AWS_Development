'''
This Lambda script checks the healtcheck SSM command IDs whether it is completed or not.
'''

import boto3
import json
import csv
import sys
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))

s3_client = boto3.client("s3",config=config)
s3_resource = boto3.resource('s3')

def PrintException():
    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    captureErr = "Line No. : " + str(lineno)  + " | ERROR: " + str(exc_obj)
    return captureErr


def fetch_data_from_config_file(S3_Bucket,S3_directory_name,TagValues,Phase):
    try:
        directory_name = S3_Folder_Name + "/" + "PATCHING/" + S3_directory_name + "/HealthCheck_SSM_CommandIDs/" + Phase + "_HC_SSM_CommandIDs_" + TagValues +".json"
        print("directory_name : ", directory_name)
        response = s3_client.get_object(Bucket=S3_Bucket, Key= directory_name)
        content = response['Body']  
        #data = content.read().decode("utf-8")   
        Config_file_data = json.loads(content.read())
        Command_Id = []
        for i in range(len(Config_file_data)):
            health_check_dic_data =  Config_file_data[i]
            command_id = health_check_dic_data['command_id']
            Command_Id.append(command_id)
        return Command_Id
    except:
        print(PrintException())

def check_command_id_staus(command_ids):
    ssm_client = boto3.client('ssm',config=config)
    print("command_ids ==> ",command_ids)
    command_id_status = []
    for command_id in command_ids:        
        response = ssm_client.list_command_invocations(CommandId=command_id,)        
        CommandInvocations_data = response['CommandInvocations']
        Instance_ids = [ sub['InstanceId'] for sub in CommandInvocations_data]
        command_id_invocation_status = [ sub['Status'] for sub in CommandInvocations_data]
        print("Instance Ids ===> " ,Instance_ids)
        print("command_id_invocation_status ===> " ,command_id_invocation_status)
        CommandInvocations_status = dict(zip(Instance_ids, command_id_invocation_status))
        print("CommandInvocations_status ==> ",CommandInvocations_status)
        status = ''
        if 'InProgress' in command_id_invocation_status:
            status = 'pending'
        if 'Success' in command_id_invocation_status:
            status = 'completed'
        if 'Failed' in command_id_invocation_status:
            status = 'completed'
        if 'TimedOut' in command_id_invocation_status:
            status = 'completed'
        if 'Cancelled' in command_id_invocation_status:
            status = 'completed'
        command_id_status.append(status)
    Command_invocation_status = dict(zip(command_ids,command_id_status))
    return Command_invocation_status
   
# command_status = check_command_id_staus(command_ids)

def lambda_handler(event,context):
    ssm_client = boto3.client('ssm',config=config)
    Patching_Type = event['Patching_Type']
    TagValues = event["PatchInstallOn"]
    global region
    region = event['region']
    print("Tag Value is : ", TagValues)
    global S3_Folder_Name   
    S3_Bucket = event["S3_Bucket"]
    S3_directory_name = event["S3_directory_name"]
    S3_Folder_Name = event['S3_Folder_Name']
    Status = event['Status']
    Phase = event['Phase']
    count = event['Count']
    count = int(count) - 1
    command_ids = fetch_data_from_config_file(S3_Bucket,S3_directory_name,TagValues,Phase)
    print(command_ids)
    command_status = check_command_id_staus(command_ids)
    print("command_status ==> ",command_status)
    command_status = check_command_id_staus(command_ids)
    print("command_status ==> ",command_status)
    status = ''
    for command_id in command_ids:
        print(command_id)
        if command_status[command_id] == 'completed':
            status = 'completed'
        if command_status[command_id] == 'pending':
            status = 'pending'
            break
            
    print("overall status ==> ",status)
    # for i in range(len(command_ids)):
    #     Command_Id_Invocation = ssm_client.list_command_invocations(CommandId = command_ids[i])
    # S3_objects = []
    # for i in range(len(command_ids)):
    #     try:
    #         response = s3_client.list_objects(
    #             Bucket = S3_Bucket,
    #             Prefix = S3_Folder_Name + "/" + "PATCHING/status-check/" + command_ids[i]
    #         )
    #         s3_key = response['Contents'][0]['Key']
    #         print(s3_key)
    #         S3_objects.append(s3_key)
    #     except:
    #         i = i + 1
    # if len(S3_objects) == len(command_ids):
    #     status = "completed"
    # else:
    #     status = "pending"
    output = {}
    output['Patching_Type'] = Patching_Type
    output['Status'] = status
    output['Count'] = count
    output['PatchInstallOn'] = TagValues
    output['S3_Bucket'] = S3_Bucket
    output['S3_directory_name'] = S3_directory_name
    output['S3_Folder_Name'] = S3_Folder_Name
    output['region'] = region
    if Phase == "pre":
        output['Phase'] = "pre"
    else:
        output['Phase'] = "post"
    # print(S3_objects)
    print(output)
    return output

if __name__ == "__main__":
    event1 = {
  "Status": "pending",
  "Count": "10",
  "PatchInstallOn": "WIN_TEST-NOV_21_2021_13_30_4HRS",
  "S3_Bucket": "dxc",
  "S3_directory_name": "NOV_2021/ap-south-1/patchJobId_90963df6-46b9-11ec-b2db-8c8caa2990d1",
  'S3_Folder_Name': 'test',
  "Phase": "post",
  "region":"ap-south-1"
}   
    lambda_handler(event1, "")

# test/PATCHING/NOV_2021/ap-south-1/patchJobId_90963df6-46b9-11ec-b2db-8c8caa2990d1/HealthCheck_SSM_CommandIDs/
# pre_HC_SSM_CommandIDs_WIN_TEST-NOV_21_2021_13_30_4HRS.json



    