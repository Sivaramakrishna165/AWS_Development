'''
This Lambda script is used to update the tag as _BY/_BN based on the status of backup
'''

import boto3
import codecs
import json,csv
import os,sys
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))

s3client = boto3.client('s3',config=config)


def PrintException():
    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    captureErr = "Line No. : " + str(lineno)  + " | ERROR: " + str(exc_obj)
    return captureErr

def update_item_dynamoDB(patchJob_id,attributeKeyName,attributeKeyValue):
    try:
        dynamodb = boto3.resource('dynamodb')
        dataItem = {}
              
        patch_table = dynamodb.Table('Ft_dxcms_patching_e2e_automation')  
        updateAttribute =  "set " + attributeKeyName + "=:data"        
        patch_table.update_item(
                Key={'patchJob_id': patchJob_id},
                UpdateExpression=updateAttribute,
                ExpressionAttributeValues={':data': attributeKeyValue},
                ReturnValues="UPDATED_NEW"
                ) 
    except:
        print(PrintException())
        
def read_csv_from_s3(S3_Bucket, S3_directory_name, instanceIdcolumn, statusColumn):
    try:
        directory_name = S3_Folder_Name + "/" + "PATCHING" + "/" + S3_directory_name + "/Backup_Reports/" + "Backup_Report_" + tagValue + ".csv"
        data = s3client.get_object(Bucket = S3_Bucket, Key = directory_name)
        instanceId = []
        status = []
        for row in csv.DictReader(codecs.getreader("utf-8")(data["Body"])):
            instanceId.append(str(row[instanceIdcolumn]))
            status.append(str(row[statusColumn]))
        InstanceId_Status_dic = {instanceId[i]: status[i] for i in range(len(instanceId))}
        return InstanceId_Status_dic
    except:
        print(PrintException())

#x  = read_csv_from_s3('dxc',"JUN_2021",'InstanceId','Status')

def tag_on_instance(instanceId,updatedTag,tag_name):
    try:
        client = boto3.client('ec2',region_name = region,config=config)
        response = client.create_tags(    
            Resources=[
                instanceId,
            ],
            Tags=[
                {
                    'Key': tag_name,
                    'Value': updatedTag
                },
            ]
        )
        print("Updated PatchInstallOn tag value as ", updatedTag)
    except:
        print(PrintException())

#tag_on_instance('i-06fc5bd182644bbd4','JUL_11_2021_8_0_5HRS_BN')

def update_tag_on_instnace(S3_Bucket, S3_directory_name,tagValue,tag_name):
    try:
        instanceIdcolumn = 'InstanceId'
        statusColumn = 'Status'
        InstanceId_Status = read_csv_from_s3(S3_Bucket, S3_directory_name, instanceIdcolumn, statusColumn)
        for instanceId, status in InstanceId_Status.items():
            if status == 'completed':
                updated_tag = tagValue + "_BY"
                print(f"Backup status of Instance ID {instanceId} : COMPLETED")
                tag_on_instance(instanceId,updated_tag,tag_name)
            else:
                updated_tag = tagValue + "_BN"
                print(f"Backup status of Instance ID {instanceId} : NOT COMPLETED")
                tag_on_instance(instanceId,updated_tag,tag_name)
    except:
        print(PrintException())

def lambda_handler(event,context):
    try:
        global tagValue,S3_Folder_Name,region
        region = event['region']
        tagValue = event['PatchInstallOn']
        Patching_Type= event['Patching_Type']
        if Patching_Type == 'Adhoc':
            tag_name = 'AdhocPatchInstallOn'
        else:
            tag_name = 'PatchInstallOn'
        S3_directory_name = event['S3_directory_name']
        S3_Folder_Name = event['S3_Folder_Name']

        patchMonth = S3_directory_name.split("/")[0]
        patchJobId = S3_directory_name.split("/")[2]
        
        update_tag_on_instnace(event['S3_Bucket'],event['S3_directory_name'],tagValue,tag_name)
        #update_item_dynamoDB(patchJobId,"backup_state_status","completed")
        return event
    except:
        print(PrintException())

        
# simple test cases
if __name__ == "__main__":
    event1 = {"PatchInstallOn": "WIN_TEST-NOV_21_2021_13_30_4HRS","S3_Bucket": "dxc","S3_directory_name": "NOV_2021/ap-south-1/patchJobId_90963df6-46b9-11ec-b2db-8c8caa2990d1","S3_Folder_Name" : "test","region":"ap-south-1"}   
    lambda_handler(event1, "")
