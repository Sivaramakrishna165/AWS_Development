'''
This Lambda script generates/updates the PatchInstallOn tag on the eligible instance to reschedule the patching activity date and time
'''

import boto3
import sys
from datetime import datetime
import json
import uuid
from botocore.config import Config
import csv
import io
import os

config=Config(retries=dict(max_attempts=10,mode='standard'))
#patch_group_order = os.environ['PatchGroupOrder']

def generate_uniqueId():
    patchJobId = "patchJobId_" + str(uuid.uuid1())
    return patchJobId

def PrintException():
    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    captureErr = "Line No. : " + str(lineno)  + " | ERROR: " + str(exc_obj)
    return captureErr

def read_ssm_parameter(name):
    ssm = boto3.client("ssm",config=config)
    ssmParameter = ssm.get_parameter(Name=name)
    ssm_parameter_value = json.loads(ssmParameter['Parameter']['Value'])
    return ssm_parameter_value
    
    
#fetch instance id list either from PatchInstallOn tags or from the cleanup report    
def fetch_instance_ids(tagvalue, patchgroup): 
    try:
        instance_ids = []
        #tag_key = 'PatchInstallOn'
        ec2_client = boto3.client('ec2',region_name = region,config=config)
        response = ec2_client.describe_instances(
        Filters=[
        {'Name': 'tag:PatchInstallOn','Values': [tagvalue +'*']},
        {'Name': 'tag:Patch Group','Values': [patchgroup]}
        ])
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                instance_ids.append(instance["InstanceId"])
        print("Instances:",len(instance_ids), instance_ids)
        
        return instance_ids
    except:
        print(PrintException())
        return []


def get_instances_from_s3(s3_file_key):
    try:
        instance_ids = []
        print(s3_file_key)
        s3client = boto3.client("s3",config=config)
        obj = s3client.get_object(Bucket=S3_bucket, Key=s3_file_key)
        data = obj['Body'].read().decode('utf-8')
        reader = csv.reader(io.StringIO(data), delimiter=',', quotechar='|')
        for row in reader:
            if row[2] == 'Tag': instance_ids.append(row[3])
        return instance_ids
    except:
        print(PrintException())

def is_new_date_after_temp(PatchInstallTemp_tag, PatchInstallOn_tag):
    try:
        # datetime(year, month, day, hour, minute, second)
        PatchInstallOn = (PatchInstallOn_tag.split('-')[1]).split('_')
        PatchInstallTemp = (PatchInstallTemp_tag.split('-')[1]).split('_')       
        
        PatchInstallOn = PatchInstallOn[2]+'/'+ PatchInstallOn[0]+'/'+ PatchInstallOn[1]
        PatchInstallTemp = PatchInstallTemp[2]+'/'+ PatchInstallTemp[0]+'/'+ PatchInstallTemp[1]       
        print("PatchInstallOn Date:", PatchInstallOn, "PatchInstallTemp Date:",PatchInstallTemp)
        
        d1 = datetime.strptime(PatchInstallOn, "%Y/%b/%d")
        d2 = datetime.strptime(PatchInstallTemp, "%Y/%b/%d")
        date_diff = (d1 - d2).days
        print("Date Difference:",date_diff)
        if date_diff > 0:
            return True
        else:
            return False       
    except:
        print(PrintException())

#update PatchInstallOn tags    
def update_patchTags(TagName, instance_ids): 
    try:
        print("Updating PatchInstallOn Tags...",TagName,instance_ids)
        ec2_client = boto3.client('ec2',region_name = region,config=config)
        
        #Get instances that have PatchInstallTemp tags
        ec2_list = ec2_client.describe_instances(InstanceIds=instance_ids)
        instance_ids_temp = {}
        PatchInstallTemp_tags = []        
        for ec2 in ec2_list['Reservations']:
            for instance in ec2["Instances"]:
                for tag in instance["Tags"]:
                    if tag["Key"] == 'PatchInstallTemp':
                        print(instance['InstanceId'], tag['Value'])
                        instance_ids_temp[instance['InstanceId']] = tag['Value']
        filtered_instance_ids = [i for i in instance_ids if i not in instance_ids_temp]
        if instance_ids_temp:
            print(instance_ids_temp)
            PatchInstallTemp_tags = list(set(instance_ids_temp.values()))
            for instance_id,PatchInstallTemp_tag in instance_ids_temp.items():
            #For instances that have PatchInstallTemp tags date before the reschedule date update PatchInstallTemp tags to PatchInstallOn tags
            #and add new reschedule tags as PatchInstallTemp tags
                if is_new_date_after_temp(PatchInstallTemp_tag, TagName): #Swap PatchInstallTemp and PatchInstallOn tag values
                    response = ec2_client.create_tags(Resources=[instance_id],
                        Tags=[{
                                'Key': "PatchInstallTemp",
                                'Value': TagName
                               },
                               {
                                'Key': "PatchInstallOn",
                                'Value': PatchInstallTemp_tag
                               },
                             ])
                    print("Updated PatchInstallTemp and PatchInstallOn tags for ", instance_id)
                else:                                                           #Only update PatchInstallOn tag
                    filtered_instance_ids.append(instance_id)
        else:
            print("No Instances have PatchInstallTemp tag!")

        #Finally Update Tags for instances where no PatchInstallTemp tags present or Only need to update PatchInstallOn tag 
        if filtered_instance_ids:
            response = ec2_client.create_tags(Resources=filtered_instance_ids,
                Tags=[{
                        'Key': "PatchInstallOn",
                        'Value': TagName
                       },
                    ])
            print("PatchInstallOn Tags updated with new value:", TagName)
    except:
        print(PrintException())
    return PatchInstallTemp_tags
    
def lambda_handler(event, context):
    global patchOrderInfo, S3_bucket, S3_Folder_Name, S3_directory_name, newpatchInstallOn, region, TagValues
    try: 
        region = event['region']
        TagValues = event['Tag_Value']
        S3_bucket = event['S3_Bucket']
        S3_directory_name = event['S3_directory_name']
        S3_Folder_Name = event['S3_Folder_Name']
        jsonTagValues = {}
        jsonTagValues['OldTagValues'] = TagValues
        jsonTagValues['TagValues'] = []
        jsonTagValues['TagMapping'] = {}
        
        for TagValue in TagValues:
            patch_group = TagValue.split('-')[0]
            newpatchInstallOn = patch_group+'-'+ event['Reschedule_date_time']+"HRS"
            
            #patchOrderInfo = read_ssm_parameter(patch_group_order)
            tagged_instances = fetch_instance_ids(TagValue,patch_group)
            
            #If no instances have that tag, probably its already cleaned up, so check for a cleanup file to get the instance list
            if not len(tagged_instances):
                print("No instances with 'PatchInstallOn' value:",TagValue)
                print("Checking for clean up file...")
                #refer to clean up file in s3 bucket and get instance ids
                bucket_key = S3_Folder_Name+'/PATCHING/'+ S3_directory_name +'/Patching-Windows-missed/'
                filename = "Deleted_tag_rule" + "_" + TagValue + ".csv"
                tagged_instances = get_instances_from_s3(bucket_key+filename)
            if tagged_instances:
                PatchInstallTemp_tags = update_patchTags(newpatchInstallOn, tagged_instances)
                if PatchInstallTemp_tags: jsonTagValues['TempTagValues'] = PatchInstallTemp_tags
                jsonTagValues['TagValues'].append(newpatchInstallOn)
                jsonTagValues['TagMapping'][newpatchInstallOn] = TagValue
        
        jsonTagValues['TagName'] = event['TagName']    
        jsonTagValues['S3_Bucket'] = event['S3_Bucket']
        jsonTagValues['S3_directory_name'] = S3_directory_name
        jsonTagValues['S3_Folder_Name'] = S3_Folder_Name
        jsonTagValues['region'] = region
        print(jsonTagValues)
        return jsonTagValues
    except:
        print(PrintException())

# simple test cases
if __name__ == "__main__":
    event1 = {
  "Tag_Value": "DEV-JUN_7_2023_6_0_3HRS",
  "region": "eu-west-3",
  "S3_Bucket": "dxcms.patchingautomation.567529657087.eu-west-3",
  "S3_directory_name": "JUN_2023/eu-west-3",
  "S3_Folder_Name": "patching_reports",
  "Reschedule_date_time" : "JUN_21_2023_6_0_4"
}
    lambda_handler(event1, "")
