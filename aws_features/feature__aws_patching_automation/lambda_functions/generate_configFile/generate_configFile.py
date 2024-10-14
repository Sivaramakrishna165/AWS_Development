'''
This Lambda script generates configuration file which has details of 
patch installation schedule date, pre-tasks schedule and patch scan schedule dates.
'''

import boto3
import os
import csv 
import json
import sys
import datetime
from dateutil import relativedelta
import uuid
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))

PatchScanTriggerDay = os.environ['PatchScanTriggerDay']

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

def create_S3_folder(S3_Bucket,S3_directory_name,S3_Folder_Name):
    s3_resource = boto3.resource('s3')
    s3_client = boto3.client('s3',config=config)
    bucket_name = S3_Bucket
    directory_name = S3_Folder_Name + "/" + "PATCHING" + "/" + S3_directory_name
    bucket = s3_resource.Bucket(bucket_name)
    s3_client.put_object(Bucket=bucket_name, Key=(directory_name+'/'))
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

def lambda_handler(event,context):
    global region,S3_Folder_Name
    global jobMonth
    Tagname = event['TagName']

    if Tagname == 'Downtime Window':
        Patch_Scan_Trigger_Day = read_ssm_parameter(PatchScanTriggerDay)
        back_up_trigger_time = os.environ['BackupTriggerTime']
        patchinstalltag = "PatchInstallOn"
        temppatchinstalltag = "PatchInstallTemp"
        #PatchGroupOrder = os.environ['PatchGroupOrder']
        #PatchGroupOrder = read_ssm_parameter(PatchGroupOrder)
    else:
        patchinstalltag = "AdhocPatchInstallOn"
        Patch_Scan_Trigger_Day = 0
        back_up_trigger_time = os.environ['AdhocBackupTriggerTime']
        temppatchinstalltag = "AdhocPatchInstallTemp"
        #AdhocPatchGroupOrder = os.environ['AdhocPatchGroupOrder']
        #AdhocPatchGroupOrder = read_ssm_parameter(AdhocPatchGroupOrder)
    
    patch_scan_trigger_days = int(Patch_Scan_Trigger_Day)
    region = event['region']
    bucket, directory_name = create_S3_folder(event['S3_Bucket'],event['S3_directory_name'],event['S3_Folder_Name'])
    ec2_resource = boto3.resource('ec2',region_name = region)
    ec2_client = boto3.client('ec2',region_name = region,config=config)
    TagValues = event['TagValues']
    
    S3_Folder_Name = event['S3_Folder_Name']
    S3_directory_name = event['S3_directory_name']
    jobMonth = S3_directory_name.split("/")[0]
    
    configFile = {}
    configFile['executePatchInstallation'] = {}
    configFile['downtimecontacts'] = {}
    configFile['executepatchscan'] = {}
    configFile['performPreTasks'] = {}
    configFile['patchJobIds'] = {}
    cronjobsForPatchInstall = {}
    cronjobsForPatchScan = {}
    cronjobsForPeformPreTasks = {}
    downtimeContacts = {}
    patchJobIdForTagValue = {}

    localFolder = "/tmp/"

    backup_trigger_time = read_ssm_parameter(back_up_trigger_time)
    backup_trigger_time = int(backup_trigger_time)
   
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
                    {'Name':"tag:"+patchinstalltag, 'Values':[tagValue]}        
                    ]
        response_patch = ec2_client.describe_instances(Filters=ec2_filter)
        for r in response_patch['Reservations']:
            for instance in r['Instances']:
                instancelist.append(instance['InstanceId'])
        ec2_filter = [
                    {'Name':"tag:"+temppatchinstalltag, 'Values':[tagValue]}        
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
        print("DOWN TIME CONTANCTS : ", downtimeContactAll)
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
   
    configFile['executePatchInstallation'] = cronjobsForPatchInstall
    configFile['executepatchscan'] = cronjobsForPatchScan
    configFile['downtimecontacts'] = downtimeContacts        
    configFile['performPreTasks'] = cronjobsForPeformPreTasks 
    configFile['patchJobIds'] = patchJobIdForTagValue
    print(configFile)
    
    #local_folder = '/tmp/Patching_config.json'
    local_folder = localFolder + 'Patching_config.json'
    local_file = 'Patching_config.json'
    s3Key = directory_name + "/" + local_file
    
    with open(local_folder, 'w') as outfile:
        json.dump(configFile, outfile)

    bucket.upload_file(local_folder, s3Key)
    print("\n",event)
    return event
    
    
if __name__ == "__main__":
    #event1 = { "PatchInstallOnTagValues": ['APR_4_2021_14_30_4HRS', 'APR_11_2021_14_30_4HRS', 'APR_4_2021_03_30_4HRS', 'APR_18_2021_14_30_4HRS'] }
    event1 = {'TagValues': ['WIN_TEST-NOV_21_2021_13_30_4HRS'], 'S3_Bucket': 'dxc', 'S3_directory_name': 'NOV_2021/ap-south-1','S3_Folder_Name': 'test',"region":"ap-south-1"}
    #event1 = {'TagValues': ['DEV-JUL_25_2021_14_0_5HRS', 'DEV-JUL_24_2021_6_0_3HRS'], 'S3_Bucket': 'dxc', 'S3_directory_name': 'JUL_2021/ap-south-1'}

    
    lambda_handler(event1, "")