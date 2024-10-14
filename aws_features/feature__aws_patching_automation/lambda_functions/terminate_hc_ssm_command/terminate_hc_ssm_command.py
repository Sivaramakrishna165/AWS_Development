'''
This Lambda function is used to terminate the health checck SSM command if it is running beyond the mentioned time limit
'''

import boto3
import sys
import json
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))

s3_client = boto3.client("s3",config=config)

def PrintException():
    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    captureErr = "Line No. : " + str(lineno)  + " | ERROR: " + str(exc_obj)
    return captureErr

def fetch_data_from_config_file(S3_Bucket,S3_directory_name,TagValues,Phase):
    try:
        #directory_name = "PATCHING/" + S3_directory_name + "/Health_Check_Config_File/Health_Check_" + TagValues +".json"
        directory_name = S3_Folder_Name + "/" + "PATCHING/" + S3_directory_name + "/HealthCheck_SSM_CommandIDs/" + Phase + "_HC_SSM_CommandIDs_" + TagValues +".json"
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

def fetch_s3_objects(S3_Bucket,S3_directory_name,TagValues,Phase):
    command_ids = fetch_data_from_config_file(S3_Bucket,S3_directory_name,TagValues,Phase)
    S3_objects = []
    try:
        for i in range(len(command_ids)):
            response = s3_client.list_objects_v2(
                    Bucket = S3_Bucket,
                    Prefix = S3_Folder_Name + "/" + "PATCHING/status-check/" + command_ids[i]
                )
            s3_key = response['Contents'][0]['Key']
            s3_key = s3_key.split("PATCHING/status-check/")
            cmd_status = s3_key[1]
            #print("cmd_status ", type(cmd_status))
            cmd = cmd_status.split("_")
            cmd_id_in_S3 = cmd[0]
            S3_objects.append(cmd_id_in_S3)
            i = i + 1
        return S3_objects, command_ids
    except:
        print(PrintException())
        
# command_ids = ['7aa7aba5-7d99-46b4-bfe4-4ef9c36f1892','3c9e1358-36fd-4aac-84f0-553aad54b7c7']

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
# print("command_status ==> ",command_status)
# status = ''
# Command_id_to_be_terminated = []
# for command_id in command_ids:
#     print(command_id)
# #     if command_status[command_id] == 'completed':
# #         status = 'completed'
#     if command_status[command_id] == 'pending':
#         status = 'pending'
#         Command_id_to_be_terminated.append(command_id)
        
def terminate_ssm_command(Command_id_to_be_terminated):
    for cmd_id in Command_id_to_be_terminated:
        response = ssm_client.cancel_command(CommandId=cmd_id)
        print(response)
   
        
        
# print("overall status ==> ",status)   

def lambda_handler(event, context):
    count = event['Count']
    global S3_Folder_Name,region,ssm_client
    region = event['region']
    S3_Folder_Name = event['S3_Folder_Name']
    TagValues = event['PatchInstallOn']
    S3_Bucket = event['S3_Bucket']
    S3_directory_name = event['S3_directory_name']
    Phase = event['Phase']

    ssm_client = boto3.client("ssm",region_name=region,config=config)

    command_ids = fetch_data_from_config_file(S3_Bucket,S3_directory_name,TagValues)
    command_status = check_command_id_staus(command_ids)
    print("command_status ==> ",command_status)
    status = ''
    Command_id_to_be_terminated = []
    for command_id in command_ids:
        print(command_id)
        if command_status[command_id] == 'pending':
            status = 'pending'
            Command_id_to_be_terminated.append(command_id)
    if len(Command_id_to_be_terminated) != 0:
        terminate_ssm_command(Command_id_to_be_terminated)
    # S3_objects, command_ids = fetch_s3_objects(S3_Bucket,S3_directory_name,TagValues,Phase)
    # print('S3_objects', S3_objects)
    # print('command_ids',command_ids)
    # command_ids = fetch_data_from_config_file(S3_Bucket,S3_directory_name,TagValues)
    # if len(S3_objects) != 0:
    #     cancel_cmd = [x for x in command_ids if x not in S3_objects]
    #     print('cancel_cmd is ',cancel_cmd)
    #     for i in range(len(cancel_cmd)):
    #         response = ssm_client.cancel_command(CommandId = cancel_cmd[i])
    # else :
    #     print("Command IDs : ",command_ids )
    #     print("Type of the command_ids : ", type(command_ids))
    #     for cmdId in command_ids:
    #         response = ssm_client.cancel_command(CommandId = cmdId)
    return event


if __name__ == "__main__":
    #event1 = {'PatchInstallOn': 'APR_4_2021_14_0_4HRS','Count': '10', 'S3_Bucket': 'dxc', 'S3_directory_name': 'JUN_2021',"Phase":"pre"}
    #event1 = {"Status": "pending","Count": 0,"PatchInstallOn": "JUN_20_2021_14_0_4HRS","S3_Bucket": "dxc","S3_directory_name": "JUN_2021","Phase": "pre"}
    event1 = {
  "Status": "pending",
  "Count": 0,
  "PatchInstallOn": "DEV-JUL_25_2021_14_0_4HRS",
  "S3_Bucket": "dxc",
  "S3_directory_name": "JUL_2021/ap-south-1/patchJobId_cfebaa26-c9cb-11eb-ac44-76d3d9fead34",
  "Phase": "pre",
  'S3_Folder_Name': 'test',
  "region":"ap-south-1"
}
    lambda_handler(event1, "")

#{"Status": "pending","Count": 0,"PatchInstallOn": "JUN_20_2021_14_0_4HRS","S3_Bucket": "dxc","S3_directory_name": "JUN_2021","Phase": "pre"}