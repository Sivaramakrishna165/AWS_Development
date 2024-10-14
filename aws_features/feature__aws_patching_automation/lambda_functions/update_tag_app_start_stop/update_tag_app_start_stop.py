'''
This Lambda script is used to update the tag as _AY/_AN to know the status of stopping/starting application 
'''

import boto3
import sys
import json
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))

def PrintException():
    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    captureErr = "Line No. : " + str(lineno)  + " | ERROR: " + str(exc_obj)
    return captureErr

def IsObjectExists(path):
    s3 = boto3.resource('s3')
    bucket = s3.Bucket(bucket_name)
    for object_summary in bucket.objects.filter(Prefix=path):
        return True
    return False

# def update_item_dynamoDB(patchJob_id,instanceAppStatus,appAction):
#     try:
#         dynamodb = boto3.resource('dynamodb')          
#         patch_table = dynamodb.Table('Ft_dxcms_patching_e2e_automation')    
#         if appAction == "stop":
#             patch_table.update_item(
#                     Key={'patchJob_id': patchJob_id},
#                     UpdateExpression="set app_stopped_instances=:d",
#                     ExpressionAttributeValues={':d': instanceAppStatus},
#                     ReturnValues="UPDATED_NEW"
#                     ) 
#         elif appAction == "start":
#             patch_table.update_item(
#                     Key={'patchJob_id': patchJob_id},
#                     UpdateExpression="set app_started_instances=:d",
#                     ExpressionAttributeValues={':d': instanceAppStatus},
#                     ReturnValues="UPDATED_NEW"
#                     ) 
#     except:
#         print(PrintException())

def call_update_dynamodb_lambda_function(patchJob_id,attribute_name,attribute_value):
    lambda_client = boto3.client('lambda',config=config)
    dynamo_event = {'patchJob_id': patchJob_id,'attribute_name':attribute_name,'attribute_value':attribute_value}
    response = lambda_client.invoke(
        FunctionName='dxcms-pa-lam-update-dynamodb',
        Payload=json.dumps(dynamo_event)
    )

        
def extract_ssm_command_id(commandId,next_token):
    try:
        ssm_client = boto3.client('ssm',region_name = region,config=config)
        MaxRecords = 50
        if next_token == "" or next_token == None:        
            ssmCmdResults = ssm_client.list_command_invocations(CommandId=commandId,MaxResults=MaxRecords)
            try:
                next_token = ssmCmdResults['NextToken']
            except:
                next_token = None
        else:
            ssmCmdResults = ssm_client.list_command_invocations(CommandId=commandId,MaxResults=MaxRecords,NextToken=next_token)
            try:
                next_token = ssmCmdResults['NextToken']
            except:
                next_token = None
                
        for cmd_result in ssmCmdResults['CommandInvocations']:
                instanceAppStatus[cmd_result["InstanceId"]] = cmd_result["Status"] 
                
        if next_token != None:
            extract_ssm_command_id(next_token)  
        
        return instanceAppStatus
    except:
        err = PrintException()
        print(err) 
        
def update_instanceTag(instanceId,updatedTagValue,Patching_tag):   
    ec2_client = boto3.client('ec2',region_name = region,config=config)
    try:
        response = ec2_client.create_tags(
                                Resources=[
                                    instanceId,
                                ],
                                Tags=[
                                    {
                                        'Key': Patching_tag,
                                        'Value': updatedTagValue
                                    },
                                ]
                            )
    except:
        print(PrintException())

''' # This was the first approach. Now it is not used as directly getting status by extracting SSM command id output [def extract_ssm_command_id(commandId,next_token)]
def get_result(instanceId,tagValue):
    s3 = boto3.resource('s3')
    s3ObjectList = []
    S3ObjectForWindows = appFolderName + instanceId + "/awsrunPowerShellScript/runPowerShellScript/"
    S3ObjectForLinux = appFolderName + instanceId + "/awsrunShellScript/runShellScript/"
    s3ObjectList = [S3ObjectForWindows,S3ObjectForLinux]
    IsFoundFolder = False
    
    for s3Object in s3ObjectList:
        print(s3Object)
        if(IsObjectExists(s3Object)): 
            print("---------------------------Found Folder-----------------------")
            IsFoundFolder = True
            if(IsObjectExists(s3Object + "stderr")):
                print("Found stderr file")
                obj = s3.Object(bucket_name, s3Object + "stderr")
                body = obj.get()['Body'].read().decode('utf-8')
                #It means, there is no application stop/start script available. Hence, considering it is success.
                if "is not recognized" in body:
                    updatedTagValue = tagValue + "_AY"
                    print("------- ", instanceId," - IS NOT RECONNIZED")
                elif "No such file" in body:
                    updatedTagValue = tagValue + "_AY"
                    print("------- ", instanceId," - No such file")
                else:                
                    updatedTagValue = tagValue + "_AN"
                update_instanceTag(instanceId,updatedTagValue)
            elif(IsObjectExists(s3Object + "stdout")):
                print("Found stdout file")
                obj = s3.Object(bucket_name, s3Object + "stdout")
                body = obj.get()['Body'].read().decode('utf-8')
                print("BODY : ", body)
                if "success" in body:
                    print("Stopped Application successfully")
                    updatedTagValue = tagValue + "_AY"
                    update_instanceTag(instanceId,updatedTagValue)
                else:
                    print("Failed")
                    updatedTagValue = tagValue + "_AN"
                    update_instanceTag(instanceId,updatedTagValue)
    
    #Incase, if no output is generated by application script, then no folder will get created in S3. In this case, considering it is success.
    if IsFoundFolder == False:
        updatedTagValue = tagValue + "_AY"
        update_instanceTag(instanceId,updatedTagValue)
'''
   
def lambda_handler(event,context): 
    global region
    region = event['region']
    #make clients and resources from session
    ec2_client = boto3.client('ec2',region_name = region,config=config)
    ssm_client = boto3.client('ssm',region_name = region,config=config)
    
    global S3_Folder_Name
    global appFolderName
    global bucket_name
    global instanceAppStatus
    global instanceAppStartStatus

    instanceAppStatus = {}
    instanceAppStopStatus = {}
    instanceAppStartStatus = {}
    bucket_name = event['S3_Bucket']
    directory_name = event['S3_directory_name']
    appAction = event['app_action']
    commandId = event['CommandId']
    S3_Folder_Name = event['S3_Folder_Name']
    Patching_Type = event['Patching_Type']
    if Patching_Type == 'Standard':
        patching_tag = "PatchInstallOn"
    else:
        patching_tag = "AdhocPatchInstallOn"
    
    tagKey = "tag:" + patching_tag
    tagValue = event['PatchInstallOn']
    
    instancelist = []
    
    patchMonth = directory_name.split("/")[0]
    patchJob_id = directory_name.split("/")[2]
    
    print("Action for Application : ", appAction)
    if appAction == "stop":
        appFolderName = S3_Folder_Name + "/" + "PATCHING/" + directory_name + "/APPS_STOP_" + tagValue + "/" + commandId + "/"
        extract_ssm_command_id(commandId,None)
        call_update_dynamodb_lambda_function(patchJob_id,attribute_name='app_status',attribute_value='stopped')

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
            #print("Executing for Instance : ", instanceId)
            #get_result(instanceId,tagValue)
            try:
                if instanceAppStatus[instanceId] == "Success":
                    updatedTagValue = tagValue + "_AY"
                    update_instanceTag(instanceId,updatedTagValue,patching_tag)
                else:
                    #updatedTagValue = tagValue + "_AN"
                    updatedTagValue = tagValue + "_AY"
                    update_instanceTag(instanceId,updatedTagValue,patching_tag)
            except:
                #updatedTagValue = tagValue + "_AN"
                updatedTagValue = tagValue + "_AY"
                update_instanceTag(instanceId,updatedTagValue,patching_tag)
    elif appAction == "start":
        appFolderName = S3_Folder_Name + "/" + "PATCHING/" + directory_name + "/APPS_START_" + tagValue + "/" + commandId + "/"
        extract_ssm_command_id(commandId,None)
        call_update_dynamodb_lambda_function(patchJob_id,attribute_name='app_status',attribute_value='started')
    else:
        raise Exception('No valid action for application')
        
    
    jsonValues = {}
    jsonValues['Patching_Type'] = event['Patching_Type']
    jsonValues['PatchInstallOn'] = tagValue + "_AY"
    jsonValues['S3_Bucket'] = bucket_name
    jsonValues['S3_directory_name'] = directory_name
    jsonValues['S3_Folder_Name'] = S3_Folder_Name
    jsonValues['region'] = region
    print(jsonValues)
    return jsonValues

if __name__ == "__main__":
    event1 = {
  "PatchInstallOn": "DEV-JUL_25_2021_14_0_5HRS_BY",
  "CommandId": "dacdbd7f-cc9d-4fd4-861c-a27a83e25805",
  "Status": "pending",
  "Count": 1,
  "S3_Bucket": "dxc",
  "S3_directory_name": "JUL_2021/ap-south-1/patchJobId_7b69f86a-c86b-11eb-a4e3-32b48c8337c9",
  "app_action": "stop",
  'S3_Folder_Name': 'test',
  "region":"ap-south-1"
}
    lambda_handler(event1, "")
