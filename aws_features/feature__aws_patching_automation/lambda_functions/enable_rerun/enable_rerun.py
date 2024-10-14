'''
This Lambda script is used to enable the rerun of state machines. Input should be as below
Applicable value of "enable_rerun_for" parameter is either pre_task or trigger_patch or post_task
{
    "patch_job_id": "patchJobId_c64779b6-f38c-11ec-9029-1d99cf8fec36",
    "enable_rerun_for": "pre_task"
} 
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

def update_tag_on_instnace(instanceIds,updatedTag):
    try:
        client = boto3.client('ec2',config=config)
        for instanceId in instanceIds:
            response = client.create_tags(    
                Resources=[
                    instanceId,
                ],
                Tags=[
                    {
                        'Key': 'PatchInstallOn',
                        'Value': updatedTag
                    },
                ]
            )
        print("Updated PatchInstallOn tag value as ", updatedTag)
    except:
        print(PrintException())

def read_item_dynamoDB(patchJob_id,attributeKey):
    dynamodb = boto3.resource('dynamodb')
    patch_table = dynamodb.Table('Ft_dxcms_patching_e2e_automation')

    try:
        response = patch_table.get_item(Key={'patchJob_id': patchJob_id})
        itemsFromTable = response['Item']
        try:
            valueOfAttributeKey = itemsFromTable[attributeKey]
            print("Value of Attribute Key :  ",valueOfAttributeKey)
        except:
            return None
        #return response['Item']
        return valueOfAttributeKey
    except:
        print(PrintException())

def fetch_instance_ids(TagValues):
    client = boto3.client('ec2',config=config)
    try:
        instanceIds = []
        response = client.describe_instances(
            Filters=[
                {
                    'Name': 'tag:PatchInstallOn',
                    'Values': [
                         TagValues,
                    ]
                },
            ]
            )    
        for r in response['Reservations']:
            for i in r['Instances']:
                instanceIds.append(i['InstanceId'])
        return instanceIds
    except:
        print(PrintException())

def copy_checksum_files(S3_Bucket_name,source_s3_folder,dest_s3_folder):
    try:
        s3 = boto3.resource('s3')
        S3_Bucket = s3.Bucket(S3_Bucket_name)
        target_Bucket = s3.Bucket(S3_Bucket_name)

        for checksum_files in S3_Bucket.objects.filter(Prefix=source_s3_folder):
            checksum_file = checksum_files.key
            copy_source = {
                        'Bucket': S3_Bucket_name,
                        'Key': checksum_file
                        }

            target_file = dest_s3_folder + checksum_file.split("/")[len(checksum_file.split("/"))-1]
            target_Bucket.copy(copy_source, target_file)
            print(f"Checksum file has been copied to : {target_file}")
    except:
        print(PrintException())

def get_aws_account_info():
    accoundId = ""
    try:
        sts = boto3.client("sts",config=config)
        accoundId = sts.get_caller_identity()["Account"]    
    except:
        print(PrintException())
        accoundId = ""
        sys.exit(1)
    return accoundId

def lambda_handler(event,context):
    region = os.environ['AWS_REGION']
    account_id = get_aws_account_info()

    patch_job_id = event['patch_job_id']
    rerun_phase = event['enable_rerun_for']
    patchInstallOn_tag_value = read_item_dynamoDB(patch_job_id,"tagvalue")
    patch_month = read_item_dynamoDB(patch_job_id,"patch_month")
    print("Tag value of PatchInstalOn : ", patchInstallOn_tag_value)
    print("Patch Month : ", patch_month)

    S3_Bucket = "dxcms.patchingautomation." + account_id + "." + region
    source_s3_folder = "patching_reports/PATCHING/" + patch_month + "/" + region + "/CheckSumFiles_bkp/"
    dest_s3_folder = "patching_reports/PATCHING/" + patch_month + "/" + region + "/CheckSumFiles/"

    copy_checksum_files(S3_Bucket,source_s3_folder,dest_s3_folder)

    if rerun_phase == "pre_task":
        print("Action to enable rerun for Pre task")
        updated_tag_value = patchInstallOn_tag_value
        pattern_tag = patchInstallOn_tag_value + "*"

    elif rerun_phase == "trigger_patch":
        print("Action to enable rerun for Trigger Patch")
        updated_tag_value = patchInstallOn_tag_value + "_BY"
        pattern_tag = updated_tag_value + "*"

    elif rerun_phase == "post_task":
        print("Action to enable rerun for Post Task")
        updated_tag_value = patchInstallOn_tag_value + "_BY_AY"
        pattern_tag = updated_tag_value + "*"
    else:
        print("ERROR : value of enable_rerun_for is wrong. It should be either pre_task or trigger_patch or post_task")
        sys.exit(1)
    
    
    InstanceIds = fetch_instance_ids(pattern_tag)
    if InstanceIds == [] or InstanceIds == "" or InstanceIds == None:
        print(f"No Instance Id found with matching tag value : {pattern_tag} . Hence, terminating execution...")
        sys.exit(1)
    else:
        print("Found Instance Ids..")        
        update_tag_on_instnace(InstanceIds,updated_tag_value)

    return event
        
# simple test cases
if __name__ == "__main__":
    event1 = {"patch_job_id": "patchJobId_c64779b6-f38c-11ec-9029-1d99cf8fec36",
            "enable_rerun_for": "pre_task"}   
    lambda_handler(event1, "")
