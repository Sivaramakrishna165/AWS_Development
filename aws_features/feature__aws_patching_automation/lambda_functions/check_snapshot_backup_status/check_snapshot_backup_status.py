'''
This Lambda script checks the backup status which is triggered by another script whether it completes or not
'''

import boto3
from botocore.client import Config
import json
import time
import sys
import datetime
from datetime import datetime
import csv
import os
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))

def PrintException():
    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    print("Line No. : " + str(lineno)  + " | ERROR: " + str(exc_obj))
    captureErr = "ERROR: " + str(exc_obj)
    return captureErr

def read_ssm_parameter(ssm_parameter):
    try:
        ssm_client = boto3.client('ssm',config=config)
        ssmParameter = ssm_client.get_parameter(Name=ssm_parameter)
        backup_requirement_status = ssmParameter['Parameter']['Value']
        return backup_requirement_status
    except:
        print(PrintException())

def IsObjectExists(path):
    try:
        s3 = boto3.resource('s3')
        bucket = s3.Bucket(bucket_name)
        for object_summary in bucket.objects.filter(Prefix=path):
            return True
        return False
    except:
        print(PrintException())
    
#def upload_file_into_s3(Source_local,Destination_S3):    
def upload_file_into_s3(fileFullName_Local,fileFullName_S3):
    try:
        s3_resource = boto3.resource('s3', config=Config(signature_version='s3v4'))
        bucket = s3_resource.Bucket(bucket_name)
        Key = fileFullName_S3
        print("Key : ", Key)
        print("fileFullName_Local : ",fileFullName_Local)
        bucket.upload_file(fileFullName_Local, Key)
    except:
        print(PrintException())
    
def download_file_from_S3_bucket(fileFullName_Local,fileFullName_S3):
    s3client = boto3.client('s3',config=config)
    try:
        #fileFullName_Local = "c:\\temp\\report.csv"
        #Key = 'PATCHING/' + S3_directory_name + '/' + errorLogFileName
        Key = fileFullName_S3        
        s3client.download_file(bucket_name, Key, fileFullName_Local)
        return True
    except:
        print(PrintException())
        return False

def check_snapshot_backup_status():
    try:
        ec2_client = boto3.client('ec2',region_name = region,config=config)
        backup_csv_contents = open(backupReport_Local_FileFullName, "r")
        dict_backup_csv = csv.DictReader(backup_csv_contents)
        overAllStatus = []
        update_backup_status = []
        for backupColumn in dict_backup_csv:
            snapshotState = None
            snapshotId = backupColumn['SnapshotId']
            currentStatus = backupColumn['Status']
            print("Checking status of Snapshot ID : ",snapshotId)
            if currentStatus != "completed":
                responses = ec2_client.describe_snapshots(SnapshotIds=[snapshotId])
                for response in responses['Snapshots']:
                    snapshotState = response['State']
                
                print("snapshotId : ",snapshotId ," | Status : ", snapshotState)
                if snapshotState == "completed":
                    row = {'InstanceId': backupColumn['InstanceId'],
                        'RootVolumeID': backupColumn['RootVolumeID'],
                        'DiskDeviceName': backupColumn['DiskDeviceName'],
                        'SnapshotId': backupColumn['SnapshotId'],
                        'Status': snapshotState,
                        'Comments': backupColumn['Comments']}
                    overAllStatus.append("completed")
                else:
                    row = {'InstanceId': backupColumn['InstanceId'],
                        'RootVolumeID': backupColumn['RootVolumeID'],
                        'DiskDeviceName': backupColumn['DiskDeviceName'],
                        'SnapshotId': backupColumn['SnapshotId'],
                        'Status': 'Not Completed',
                        'Comments': backupColumn['Comments']}
                    overAllStatus.append("pending")
                    
                    #overAllStatus = "pending"
            else:
                row = {'InstanceId': backupColumn['InstanceId'],
                    'RootVolumeID': backupColumn['RootVolumeID'],
                    'DiskDeviceName': backupColumn['DiskDeviceName'],
                    'SnapshotId': backupColumn['SnapshotId'],
                    'Status': backupColumn['Status'],
                    'Comments': backupColumn['Comments']} 
                overAllStatus.append("completed")
            
            print("row =======> ",row)
            update_backup_status.append(row)
            
        #print(update_backup_status)
        backup_csv_contents.close()
        backup_csv_contents = open(backupReport_Local_FileFullName, "w", newline='')
        headers = ['InstanceId', 'RootVolumeID', 'DiskDeviceName', 'SnapshotId', 'Status','Comments']
        data = csv.DictWriter(backup_csv_contents, delimiter=',', fieldnames=headers)
        data.writerow(dict((heads, heads) for heads in headers))
        data.writerows(update_backup_status)
        backup_csv_contents.close()
        
        print("OverallStatus List Value : ",overAllStatus)
        status = "pending"
        if "pending" in overAllStatus:
            status = "pending"
        else:
            status = "completed"
            
        return status
    except:
        PrintException()


def check_ami_backup_status():
    try:
        ec2_client = boto3.client('ec2',region_name = region,config=config)
        backup_csv_contents = open(backupReport_Local_FileFullName, "r")
        dict_backup_csv = csv.DictReader(backup_csv_contents)
        overAllStatus = []
        update_backup_status = []
        ami_states = ['invalid','deregistered','transient','failed','error']
        for backupColumn in dict_backup_csv:
            snapshotState = None
            snapshotId = backupColumn['AMI_ID']
            currentStatus = backupColumn['Status']
            print("Checking status of AMI ID : ",snapshotId)
            if currentStatus != "completed":
                responses = ec2_client.describe_images(ImageIds=[snapshotId,])
                # for response in responses['ImageId']:
                #     snapshotState = response['State']
                snapshotState = responses['Images'][0]['State']
                print("AMI ID : ",snapshotId ," | Status : ", snapshotState)
                if snapshotState == "available":
                    row = {'InstanceId': backupColumn['InstanceId'],
                        'BackupType': backupColumn['BackupType'],
                        'AMI_Name': backupColumn['AMI_Name'],
                        'AMI_ID': backupColumn['AMI_ID'],
                        'Status': 'completed',
                        'Comments': backupColumn['Comments']}
                    overAllStatus.append("completed")
                elif snapshotState in ami_states:
                    row = {'InstanceId': backupColumn['InstanceId'],
                        'BackupType': backupColumn['BackupType'],
                        'AMI_Name': backupColumn['AMI_Name'],
                        'AMI_ID': backupColumn['AMI_ID'],
                        'Status': snapshotState,
                        'Comments': backupColumn['Comments']}
                    overAllStatus.append("completed")
                else:
                    row = {'InstanceId': backupColumn['InstanceId'],
                        'BackupType': backupColumn['BackupType'],
                        'AMI_Name': backupColumn['AMI_Name'],
                        'AMI_ID': backupColumn['AMI_ID'],
                        'Status': 'Not Completed',
                        'Comments': backupColumn['Comments']}
                    overAllStatus.append("pending")
                    
                    #overAllStatus = "pending"
            else:
                row = {'InstanceId': backupColumn['InstanceId'],
                    'BackupType': backupColumn['BackupType'],
                    'AMI_Name': backupColumn['AMI_Name'],
                    'AMI_ID': backupColumn['AMI_ID'],
                    'Status': backupColumn['Status'],
                    'Comments': backupColumn['Comments']} 
                overAllStatus.append("completed")
            
            print("row =======> ",row)
            update_backup_status.append(row)
            
        #print(update_backup_status)
        backup_csv_contents.close()
        backup_csv_contents = open(backupReport_Local_FileFullName, "w", newline='')
        headers = ['InstanceId', 'BackupType', 'AMI_Name', 'AMI_ID', 'Status','Comments']
        data = csv.DictWriter(backup_csv_contents, delimiter=',', fieldnames=headers)
        data.writerow(dict((heads, heads) for heads in headers))
        data.writerows(update_backup_status)
        backup_csv_contents.close()
        
        print("OverallStatus List Value : ",overAllStatus)
        status = "pending"
        if "pending" in overAllStatus:
            status = "pending"
        else:
            status = "completed"
            
        return status
    except:
        PrintException()

def lambda_handler(event, context):
    global bucket_name
    global S3_directory_name
    global backupReport_Local_FileFullName
    global S3_Folder_Name,region
    #global overAllStatus
    #overAllStatus = None
    count = event['count']
    count = int(count) - 1
    region = event['region']
    bucket_name = event['S3_Bucket']
    S3_directory_name = event['S3_directory_name']
    S3_Folder_Name = event['S3_Folder_Name']
    Patching_Type= event['Patching_Type']
    if Patching_Type == 'Adhoc':
        ssm_parameter = os.environ['AdhocBackupOptions'] #'/DXC/AdhocPatchingAutomation/Backup_Options'
    else:
        ssm_parameter = os.environ['BackupOptions'] #'/DXC/PatchingAutomation/Backup_Options'
            
    tagValue = event['PatchInstallOn']
    backupReportFileName = "Backup_Report_" + tagValue + ".csv"
    
    # backupReport_Local_Folder = "C:\\temp\\"
    backupReport_Local_Folder = "/tmp/"    
    backupReport_Local_FileFullName = backupReport_Local_Folder + backupReportFileName
    
    backupReport_S3_Folder = S3_Folder_Name + "/" + 'PATCHING/' + S3_directory_name + '/Backup_Reports/'
    backupReport_S3_FullFileName = backupReport_S3_Folder + backupReportFileName
    
    print("Downloading Backup Report from S3 : ",backupReport_S3_FullFileName)
    if (IsObjectExists(backupReport_S3_FullFileName)):
        print("Downloaded Bakup report to tmp folder")
        download_file_from_S3_bucket(backupReport_Local_FileFullName,backupReport_S3_FullFileName)
    else:
        print("Backup report is not available at : ", backupReport_S3_FullFileName)
        
    if os.path.exists(backupReport_Local_FileFullName):
        backup_type = read_ssm_parameter(ssm_parameter)
        if backup_type == 'ROOTVOL':
            status = check_snapshot_backup_status()
        if backup_type == 'AMI':
            status = check_ami_backup_status()
    else:
        print("Cant find Backup Report.. Quitting")
        sys.exit(1)
    
    upload_file_into_s3(backupReport_Local_FileFullName,backupReport_S3_FullFileName)    
    
    jsonValues = {}
    jsonValues['Patching_Type'] = Patching_Type
    jsonValues['PatchInstallOn'] = tagValue
    jsonValues['S3_Bucket'] = bucket_name
    jsonValues['S3_directory_name'] = S3_directory_name
    jsonValues['count'] = count
    jsonValues['S3_Folder_Name'] = S3_Folder_Name
    jsonValues['region'] = region
    if status == "pending":
        jsonValues['status'] = "pending"
    else:
        jsonValues['status'] = "completed"
        
    print(jsonValues)
    return jsonValues
  
    
# simple test cases
if __name__ == "__main__":
    #event1 = {"Action": "enable"}
    event1 = {"PatchInstallOn": "WIN_TEST-JAN_9_2022_13_30_4HRS","S3_Bucket": "dxc","S3_directory_name": "DEC_2021/ap-south-1/patchJobId_c096825b-5655-11ec-bdc0-3d9598f53224","count": 10,"S3_Folder_Name" : "Test","region":"ap-south-1"}
    #event1 = {"backup": "yes",'S3_Bucket': 'dxc', 'S3_directory_name': 'APR_2021'}

    lambda_handler(event1, "")