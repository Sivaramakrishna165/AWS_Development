'''
This Lambda script generates configuration file which has details of 
patch installation schedule date, pre-tasks schedule and patch scan schedule dates.
'''

import boto3
import csv 
import json
import sys
import datetime
import uuid
from botocore.config import Config
import os

config=Config(retries=dict(max_attempts=10,mode='standard'))

patch_scan_day = os.environ['PatchScanTriggerDay']
backup_time = os.environ['BackupTriggerTime']

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
        ssmParameterValue = ssmParameter['Parameter']['Value']
        return ssmParameterValue
    except:
        print(PrintException())
        
#Check to see if path exists on S3
def path_exists(bucket_name, path):
    s3client = boto3.client('s3', config=config)
    exists=False
    try:
        result = s3client.list_objects_v2(Bucket=bucket_name, Prefix=path)
        if 'Contents' in result: 
            exists=True
    except:
        print(PrintException())
    return exists
    
#Create folder not needed if already exists
def create_S3_folder(S3_Bucket,S3_directory_name,S3_Folder_Name):
    s3_resource = boto3.resource('s3')
    bucket = s3_resource.Bucket(S3_Bucket)
    directory_name = S3_Folder_Name + "/" + "PATCHING" + "/" + S3_directory_name
    if path_exists(S3_Bucket,directory_name):
        print(S3_Bucket, directory_name, "exists!")
        return bucket, directory_name
    else:
        print(S3_Bucket, directory_name, "doesn't exist. Creating new path...")
        s3_client = boto3.client('s3',config=config)
        s3_client.put_object(Bucket=S3_Bucket, Key=(directory_name+'/'))
        return bucket, directory_name

def get_aws_account_info():
    accoundId = ""
    try:
        sts = boto3.client("sts",config=config)
        accoundId = sts.get_caller_identity()["Account"]    
    except:
        print(PrintException())
        accoundId = ""
    return accoundId
    
def generate_patchId():
    try:
        pid = "patchJobId_" + str(uuid.uuid1())
        return pid
    except:
        print(PrintException())
        
def update_item_dynamoDB(patchJob_ids):
    try:
        attributeKeyName = 'patch_job_status'
        attributeKeyValue = 'rescheduled'
        dynamodb = boto3.resource('dynamodb')  
        patch_table = dynamodb.Table('Ft_dxcms_patching_e2e_automation')
        for patchJob_id in patchJob_ids:
            updateAttribute =  "set " + attributeKeyName + "=:data"        
            patch_table.update_item(
                Key={'patchJob_id': patchJob_id},
                UpdateExpression=updateAttribute,
                ExpressionAttributeValues={':data': attributeKeyValue},
                ReturnValues="UPDATED_NEW"
                ) 
    except:
        print(PrintException())
   
def create_item_dynamoDB(patchJob_id,cloudwatchRuleNameData,cloudwatchRuleCronjobData,downtimeContactAll,tagValue):
    try:
        dynamodb = boto3.resource('dynamodb')
        dataItem = {}
        
        accoundId = get_aws_account_info()
        
        patch_table = dynamodb.Table('Ft_dxcms_patching_e2e_automation')
        dataItem['patchJob_id'] = patchJob_id
        dataItem['aws_account_id'] = accoundId
        dataItem['aws_region'] = region
        dataItem['patch_job_status'] = "schedule-in-progress"
        dataItem['patch_month'] = jobMonth
        dataItem['cloudwatch_rule_names'] = cloudwatchRuleNameData
        dataItem['cloudwatch_rule_cronjobs'] = cloudwatchRuleCronjobData
        dataItem['downtime_contacts'] = downtimeContactAll
        dataItem['tagvalue'] = tagValue
        dataItem['backup_state_status'] = "schedule-in-progress"
        patch_table.put_item(Item=dataItem)
    except:
        print(PrintException())
   
def read_data_from_config_file(S3_Bucket, S3_directory_name):
    try:
        s3client = boto3.client('s3',config=config)
        directory_name = S3_Folder_Name + "/" + "PATCHING" + "/" + S3_directory_name + "/" + "Patching_config.json"
        response = s3client.get_object(Bucket=S3_Bucket, Key=directory_name)
        content = response['Body']
        config_dict = json.loads(content.read())
        #print(type(config_dict), config_dict)
    except:
        print(PrintException())
    return config_dict
    
    
def lambda_handler(event,context):
    global region, S3_Folder_Name, jobMonth

    region = event['region']
    S3_Folder_Name = event['S3_Folder_Name']
    S3_directory_name = event['S3_directory_name']
    jobMonth = S3_directory_name.split("/")[0]
    OldTagValues = event['OldTagValues']
    TagValues = event['TagValues']
    S3_Bucket = event['S3_Bucket']
    TempTagValues = []
    if 'TempTagValues' in event.keys():
        TempTagValues = event['TempTagValues']
    
    Patch_Scan_Trigger_Day = read_ssm_parameter(patch_scan_day)
    patch_scan_trigger_days = int(Patch_Scan_Trigger_Day)
    backup_trigger_time = read_ssm_parameter(backup_time)
    backup_trigger_time = int(backup_trigger_time)
    
    bucket, directory_name = create_S3_folder(S3_Bucket,S3_directory_name, S3_Folder_Name)
    ec2_resource = boto3.resource('ec2',region_name = region)
    ec2_client = boto3.client('ec2',region_name = region,config=config)
    
    #Read existing data from config file
    configFile = read_data_from_config_file(S3_Bucket, S3_directory_name)
    print("ExistingConfigfile:",configFile)
    old_patch_jobs = {}
    for tag in OldTagValues:
        old_patch_jobs[tag] = configFile['patchJobIds'][tag]
    
    #Remove old tag data from configFile
    key_list = list(configFile.keys())
    for key in key_list:
        configValues = list(configFile[key].keys())
        for tag in OldTagValues:
            for value in configValues:
                if (tag in value) and (tag not in TempTagValues):
                    print("OldValue:", value)
                    del configFile[key][value]
    print("UpdatedConfigFile:", configFile)

    cronjobsForPatchInstall = {}
    cronjobsForPatchScan = {}
    cronjobsForPeformPreTasks = {}
    downtimeContacts = {}
    patchJobIdForTagValue = {}
    
    # localFolder = "c:\\temp\\"
    localFolder = "/tmp/"


    for tagValue in TagValues:
        
        instancelist = []
        downtimeContactTag = []
        downtimeContactAll = ""
        CWRuleName_InstallPatch = ""
        CWRuleName_ExecutePatchScan = ""
        cloudwatchRuleNameData = {}
        cloudwatchRuleCronjobData = {}
        
        cronjobDate = ""
        cronjobDateForPatchScan = ""
        cronjobsDateForPreTasks = ""
        
        tagValue1 = tagValue.split("-")[1]
        
        minutes = tagValue1.split("_")[4]
        hours = tagValue1.split("_")[3]
        date = tagValue1.split("_")[1]
        month = tagValue1.split("_")[0]
        year = tagValue1.split("_")[2]
        cronjobDate = minutes + " " + hours + " " + date + " " + month + " " + "?" + " " + year
        CWRuleName_InstallPatch = "Install_Patch_" + tagValue
        cronjobsForPatchInstall[CWRuleName_InstallPatch] = cronjobDate
        #print("PATCH INSTALL => ", cronjobDate)
        
        patchInstallDate_str = str(date) + "-" +  str(month) + "-" + str(year) + "-" + str(hours) + "-" + str(minutes)
        patchInstallDate = datetime.datetime.strptime(patchInstallDate_str, '%d-%b-%Y-%H-%M')
        #print("1. PATCH INSTALL DATE (patchInstallDate): ", patchInstallDate)
        
        patchScanDate = patchInstallDate + datetime.timedelta(days= -patch_scan_trigger_days)
        #print("PATCH SCAN EXECUTE DATE : ",patchScanDate)
        #print("2. PATCH INSTALL DATE (patchInstallDate): ", patchInstallDate)
        
        patchScanDate_str = str(patchScanDate).split(" ")[0]
        date = patchScanDate_str.split("-")[2]
        month = patchScanDate_str.split("-")[1]
        year = patchScanDate_str.split("-")[0]
        
        patchScanDate_str = str(patchScanDate).split(" ")[1]
        hours = patchScanDate_str.split(":")[0]
        minutes = patchScanDate_str.split(":")[1]
        cronjobDateForPatchScan = minutes + " " + hours + " " + date + " " + month + " " + "?" + " " + year
        CWRuleName_ExecutePatchScan = "PatchScan_" + tagValue
        cronjobsForPatchScan[CWRuleName_ExecutePatchScan] = cronjobDateForPatchScan
        
        #print("PATCH INSTALL DATE (patchInstallDate): ", patchInstallDate)
        performPreTasksDate = patchInstallDate + datetime.timedelta(hours= -backup_trigger_time)
        #print("Pre Tasks Execute on : ",performPreTasksDate)
        
        performPreTasks_str = str(performPreTasksDate).split(" ")[0]
        date = performPreTasks_str.split("-")[2]
        month = performPreTasks_str.split("-")[1]
        year = performPreTasks_str.split("-")[0]
        
        performPreTasks_str = str(performPreTasksDate).split(" ")[1]
        hours = performPreTasks_str.split(":")[0]
        minutes = performPreTasks_str.split(":")[1]
        cronjobsDateForPreTasks = minutes + " " + hours + " " + date + " " + month + " " + "?" + " " + year
        CWRuleName_performPreTasks = "Peform_PreTask_" + tagValue
        cronjobsForPeformPreTasks[CWRuleName_performPreTasks] = cronjobsDateForPreTasks
        
        #TO create Patch CheckSum file to create Patch Scan report using generate_PatchScan_report.py. This will be input to that script
        patchCheckSumDict = {"pendingServers":[]};
        local_folder_patchCheckSum = localFolder + 'PatchCheckSum_' + tagValue + '.json'
        #local_folder_patchCheckSum = '/tmp/PatchCheckSum_' + tagValue + '.json'
        pre_patchCheckSum_fileName = 'Pre_PatchCheckSum_' + tagValue + '.json'
        post_patchCheckSum_fileName = 'Post_PatchCheckSum_' + tagValue + '.json'

        schedulephase_patchCheckSum_fileName = 'Schedulephase_PatchCheckSum_' + tagValue + '.json'
        s3Key_pre_patchCheckSum = directory_name + "/CheckSumFiles/" + pre_patchCheckSum_fileName
        s3Key_post_patchCheckSum = directory_name + "/CheckSumFiles/" + post_patchCheckSum_fileName
        s3Key_schedulephase_patchCheckSum = directory_name + "/CheckSumFiles/" + schedulephase_patchCheckSum_fileName

        schedulephase_patchCheckSum_fileName_bkp = 'Schedulephase_PatchCheckSum_' + tagValue + '.json'
        s3Key_pre_patchCheckSum_bkp = directory_name + "/CheckSumFiles_bkp/" + pre_patchCheckSum_fileName
        s3Key_post_patchCheckSum_bkp = directory_name + "/CheckSumFiles_bkp/" + post_patchCheckSum_fileName
        s3Key_schedulephase_patchCheckSum_bkp = directory_name + "/CheckSumFiles_bkp/" + schedulephase_patchCheckSum_fileName_bkp
        
        serverCheckSumDict = {"pendingServers":[]};
        local_folder_serverCheckSum = localFolder + 'PatchCheckSum_' + tagValue + '.json'
        #local_folder_serverCheckSum = '/tmp/PatchCheckSum_' + tagValue + '.json'
        local_file_serverCheckSum = 'ServerCheckSum_' + tagValue + '.json'
        s3Key_serverCheckSum = directory_name + "/CheckSumFiles/" + local_file_serverCheckSum
        s3Key_serverCheckSum_bkp = directory_name + "/CheckSumFiles_bkp/" + local_file_serverCheckSum
                        
        ec2_filter = [
                    {'Name':"tag:PatchInstallOn", 'Values':[tagValue]}        
                    ]
        response_patch = ec2_client.describe_instances(Filters=ec2_filter)
        for r in response_patch['Reservations']:
            for instance in r['Instances']:
                instancelist.append(instance['InstanceId'])
        ec2_filter = [
                    {'Name':"tag:PatchInstallTemp", 'Values':[tagValue]}        
                    ]
        response_temp = ec2_client.describe_instances(Filters=ec2_filter)
        for r in response_temp['Reservations']:
            for instance in r['Instances']:
                instancelist.append(instance['InstanceId'])
        
        print("Instance list is ",instancelist)        
        if instancelist:
            for instance in instancelist:
                patchCheckSumDict["status"] = "pending"
                patchCheckSumDict["pendingServers"].append(instance)
                
                serverCheckSumDict["status"] = "pending"
                serverCheckSumDict["pendingServers"].append(instance)
                
                ec2instance = ec2_resource.Instance(instance)
                downtimeContactTagValue = "notfound@dxc.com"
                for tag in ec2instance.tags:
                    if tag["Key"] == 'Downtime Contacts':
                        downtimeContactTagValue = tag["Value"]
                downtimeContactAll = downtimeContactAll + downtimeContactTagValue + ";"
        downtimeContacts[tagValue] = downtimeContactAll
        #print("DOWN TIME CONTANCTS : ", downtimeContactAll)
        cloudwatchRuleNameData["patch_install"] = CWRuleName_InstallPatch
        cloudwatchRuleNameData["patch_scan"] = CWRuleName_ExecutePatchScan
        cloudwatchRuleNameData["perform_pretasks"] = CWRuleName_performPreTasks
        
        cloudwatchRuleCronjobData["patch_install"] = cronjobDate
        cloudwatchRuleCronjobData["patch_scan"] = cronjobDateForPatchScan
        cloudwatchRuleCronjobData["perform_pretasks"] = cronjobsDateForPreTasks
        
        #cloudwatchRuleDowntimeContanctsData[patch_install] = downtimeContactAll

        
        patchJob_id = generate_patchId()
        patchJobIdForTagValue[tagValue] = patchJob_id
        patchCheckSumDict["patchJob_id"] = patchJob_id
        serverCheckSumDict["patchJob_id"] = patchJob_id
        create_item_dynamoDB(patchJob_id,cloudwatchRuleNameData,cloudwatchRuleCronjobData,downtimeContactAll,tagValue)
        
        allowed_path = localFolder + 'PatchCheckSum_' + tagValue + '.json'

        if local_folder_patchCheckSum == allowed_path and local_folder_serverCheckSum == allowed_path:
            with open(local_folder_patchCheckSum, 'w') as outfile:
                json.dump(patchCheckSumDict, outfile)
            bucket.upload_file(local_folder_patchCheckSum, s3Key_pre_patchCheckSum)
            
            with open(local_folder_patchCheckSum, 'w') as outfile:
                json.dump(patchCheckSumDict, outfile)
            bucket.upload_file(local_folder_patchCheckSum, s3Key_post_patchCheckSum)
    
            with open(local_folder_patchCheckSum, 'w') as outfile:
                json.dump(patchCheckSumDict, outfile)
            bucket.upload_file(local_folder_patchCheckSum, s3Key_schedulephase_patchCheckSum)
            
            with open(local_folder_serverCheckSum, 'w') as outfile:
                json.dump(serverCheckSumDict, outfile)
            bucket.upload_file(local_folder_serverCheckSum, s3Key_serverCheckSum)
    
            # ======== create backup files ============
    
            with open(local_folder_patchCheckSum, 'w') as outfile:
                json.dump(patchCheckSumDict, outfile)
            bucket.upload_file(local_folder_patchCheckSum, s3Key_pre_patchCheckSum_bkp)
            
            with open(local_folder_patchCheckSum, 'w') as outfile:
                json.dump(patchCheckSumDict, outfile)
            bucket.upload_file(local_folder_patchCheckSum, s3Key_post_patchCheckSum_bkp)
    
            with open(local_folder_patchCheckSum, 'w') as outfile:
                json.dump(patchCheckSumDict, outfile)
            bucket.upload_file(local_folder_patchCheckSum, s3Key_schedulephase_patchCheckSum_bkp)
            
            with open(local_folder_serverCheckSum, 'w') as outfile:
                json.dump(serverCheckSumDict, outfile)
            bucket.upload_file(local_folder_serverCheckSum, s3Key_serverCheckSum_bkp)
        else:
            raise RuntimeError('Filepath falls outside the base directory')
   
    configFile['executePatchInstallation'].update(cronjobsForPatchInstall)
    configFile['executepatchscan'].update(cronjobsForPatchScan)
    configFile['downtimecontacts'].update(downtimeContacts)   
    configFile['performPreTasks'].update(cronjobsForPeformPreTasks) 
    configFile['patchJobIds'].update(patchJobIdForTagValue)
    print("FinalConfigFile:", configFile)
    
    #local_folder = '/tmp/Patching_config.json'
    local_folder = localFolder + 'Patching_config.json'
    local_file = 'Patching_config.json'
    s3Key = directory_name + "/" + local_file
    
    with open(local_folder, 'w') as outfile:
        json.dump(configFile, outfile)

    bucket.upload_file(local_folder, s3Key)
    update_item_dynamoDB(list(old_patch_jobs.values()))
    event['OldTagValues'] = old_patch_jobs
    print("\n",event)
    return event
    
    
if __name__ == "__main__":
    event1 = {
  "TagValues": ["DEV-JUN_30_2023_6_0_3HRS", "PROD-JUN_30_2023_6_0_3HRS"],
  "S3_Bucket": "dxcms.patchingautomation.567529657087.eu-west-3",
  "S3_directory_name": "JUN_2023/eu-west-3",
  "S3_Folder_Name": "patching_reports",
  "region": "eu-west-3"
}


    lambda_handler(event1, "")
