'''
This Lambda script update the status of patch installation of instances and recorded into DynamoDB
'''

import boto3
import json,sys
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))

        
def PrintException():
    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    captureErr = "Line No. : " + str(lineno)  + " | ERROR: " + str(exc_obj)
    return captureErr

def read_item_dynamoDB(patchJob_id):
    dynamodb = boto3.resource('dynamodb')
    patch_table = dynamodb.Table('Ft_dxcms_patching_e2e_automation')

    try:
        response = patch_table.get_item(Key={'patchJob_id': patchJob_id})
        itemsFromTable = response['Item']
        
        patchInstallStatusOfInstances = itemsFromTable["patch_installed_instances"]
        print('patchInstallStatusOfInstances:',patchInstallStatusOfInstances)
        #print("=====> ",patchInstallStatusOfInstances['i-06fc5bd182644bbd4434343'])
        return response['Item']
    except:
        print(PrintException())

def update_item_dynamoDB(patchJob_id,instancePatchStatus):
    try:
        dynamodb = boto3.resource('dynamodb')
        dataItem = {}
              
        patch_table = dynamodb.Table('Ft_dxcms_patching_e2e_automation')
        patch_table.update_item(
                Key={'patchJob_id': patchJob_id},
                UpdateExpression="set patch_installed_instances=:d",
                ExpressionAttributeValues={':d': instancePatchStatus},
                ReturnValues="UPDATED_NEW"
                )
    except:
        print(PrintException())
        
def extract_ssm_command_id(commandId,next_token):
    try:
        ssm_client = boto3.client('ssm',region_name = region,config=config)
        MaxRecords = 50
        if next_token == "" or next_token == None:
            ssmCmdResults = ssm_client.list_command_invocations(CommandId=commandId,MaxResults=MaxRecords)
            try:
                next_token = ssmCmdResults['NextToken']
                print('next_token',next_token)
            except:
                next_token = None
                print('next_token',next_token)
        else:
            ssmCmdResults = ssm_client.list_command_invocations(CommandId=commandId,MaxResults=MaxRecords,NextToken=next_token)
            try:
                next_token = ssmCmdResults['NextToken']
                print('next_token',next_token)
            except:
                next_token = None
                print('next_token',next_token)
                
        for cmd_result in ssmCmdResults['CommandInvocations']:
                instancePatchStatus[cmd_result["InstanceId"]] = cmd_result["Status"]

        print(instancePatchStatus)
                
        if next_token != None:
            extract_ssm_command_id(commandId,next_token)
        
        return instancePatchStatus
    except:
        err = PrintException()
        print(err)
        

def lambda_handler(event,context):
    try:
        print('event:' ,event)
        global instancePatchStatus,S3_Folder_Name,region,commandId
        instancePatchStatus = {}
        S3_Folder_Name = event['S3_Folder_Name']
        Patching_Type = event['Patching_Type']
        tagValue = event['PatchInstallOn']
        bucket_name = event['S3_Bucket']
        S3_directory_name = event['S3_directory_name']
        commandId = event['CommandId']
        region = event['region']
        patchMonth = S3_directory_name.split("/")[0]
        patchJob_id = S3_directory_name.split("/")[2]
    
        instancePatchStatus = extract_ssm_command_id(commandId,None)
        update_item_dynamoDB(patchJob_id,instancePatchStatus)
        
        #read_item_dynamoDB(patchJob_id)
            
        jsonValues = {}
        jsonValues['Patching_Type'] = Patching_Type
        jsonValues['PatchInstallOn'] = tagValue
        jsonValues['S3_Bucket'] = bucket_name
        jsonValues['S3_directory_name'] = S3_directory_name
        jsonValues['CommandId'] = commandId
        jsonValues['Status'] = "pending"
        jsonValues['app_action'] = "start"
        jsonValues['S3_Folder_Name'] = S3_Folder_Name
        jsonValues['region'] = region
        print(jsonValues)
        return jsonValues
    except:
        print(PrintException())
        
if __name__ == "__main__":
    event1 = {"PatchInstallOn": "DEV-JUN_20_2021_14_0_5HRS_BY_AY","CommandId": "0bbd117e-4110-4fd0-aba6-0418bb660460","S3_Bucket": "dxc","S3_directory_name": "JUN_2021/ap-south-1/patchJobId_98d80322-c0a9-11eb-b95e-5f544c2b0dea","region":"ap-south-1"}
    lambda_handler(event1, "")

