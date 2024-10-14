'''
This Lambda script is used to trigger the root volumee/AM backup based on the SSM paramter configuration
'''

import boto3
from botocore.client import Config
import json
import time
import sys
import datetime
from dateutil import relativedelta
import csv
import os
from botocore.config import Config
from botocore.exceptions import ClientError

config=Config(retries=dict(max_attempts=10,mode='standard'))


def PrintException():
    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    print("Line No. : " + str(lineno)  + " | ERROR: " + str(exc_obj))
    captureErr = "ERROR: " + str(exc_obj)
    return captureErr


def call_update_dynamodb_lambda_function(patchJob_id,attribute_name,attribute_value):
    lambda_client = boto3.client('lambda',config=config)
    dynamo_event = {'patchJob_id': patchJob_id,'attribute_name':attribute_name,'attribute_value':attribute_value}
    response = lambda_client.invoke(
        FunctionName='dxcms-pa-lam-update-dynamodb',
        Payload=json.dumps(dynamo_event)
    )


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
       
def write_csv_file(instanceId,rootVolumeId,rootDeviceName,snapshot_id,status,comments):
    try:
        with open(backupReport_Local_FullFileName, 'a', newline='') as csvfile:
            filewriter = csv.writer(csvfile, delimiter=',')
            filewriter.writerow([instanceId,rootVolumeId,rootDeviceName,snapshot_id,status,comments])
    except:
        print(PrintException())

def read_ssm_parameter(ssm_parameter):
    try:
        ssm_client = boto3.client('ssm',config=config)
        ssmParameter = ssm_client.get_parameter(Name=ssm_parameter)
        backup_requirement_status = ssmParameter['Parameter']['Value']
        return backup_requirement_status
    except:
        print(PrintException())
        
def fetch_image_id(instance_id):
    try:
        ec2 = boto3.resource('ec2')
        instance = ec2.Instance(instance_id)
        ImageId = instance.image_id
        return ImageId
    except:
        print(PrintException())

def get_name_of_instance(instance):
    try:
        print(f"Getting Instance name of instnace id {instance}")
        ec2_resource = boto3.resource('ec2')
        running_instances = ec2_resource.instances.filter(InstanceIds=[instance])
        name = ""
        for instance in running_instances:
            name = ""
            if instance.tags is not None:
                for tag in instance.tags:
                    if 'Name' == tag['Key']:
                        name = tag['Value']
    except:
        print(PrintException())
    return name

def backup_root_volumes(tagValue,ec2_filter,ssm_parameter):
    ec2_client = boto3.client('ec2',region_name = region,config=config)
    backup_requirement = read_ssm_parameter(ssm_parameter)
    snapshotDescription = "PatchingAutomation_" + [tagValue][0]

    snapshotTagKey = "DeleteOn"
    deletion_snapshot_date = datetime.date.today() + relativedelta.relativedelta(days=30)
    snapshotTagValue = deletion_snapshot_date.strftime("%Y-%m-%d")
    
    response = ec2_client.describe_instances(Filters=ec2_filter)
    if response['Reservations'] == [] or response['Reservations'] == None:
        print(f"ERROR : There is no instance found with filter : {ec2_filter} . Hence, terminating the execution....")
        sys.exit(1)
    for r in response['Reservations']:
        for instance in r['Instances']:
            if backup_requirement == "ROOTVOL":
                print("Configured Backup type is ROOTVOL")
                instanceId = None
                rootVolumeId = None
                snapshot_id = None
                instanceId = instance['InstanceId']
                
                name = get_name_of_instance(instanceId)
                
                rootDeviceName = instance['RootDeviceName']
                for blockStorage in instance['BlockDeviceMappings']:
                    if blockStorage['DeviceName'] == rootDeviceName:
                        rootVolumeId = blockStorage["Ebs"]["VolumeId"]
            
                print("Instance ID is : ", instanceId)
                #trigger snapshot backup
                print("Root Volume ID : ", rootVolumeId)
                if rootVolumeId != None:
                    try:
                        response = ec2_client.create_snapshot(
                                Description= snapshotDescription,
                                VolumeId= rootVolumeId,
                                TagSpecifications=[
                                    {
                                        'ResourceType': 'snapshot',
                                        'Tags': [
                                            {
                                                'Key': snapshotTagKey,
                                                'Value': snapshotTagValue
                                            },
                                            {
                                            
                                                'Key': 'Name',
                                                'Value': 'InstanceId:Ft_Patch_Automation_' + str(instanceId)
                                            },
                                            {
                                            
                                                'Key': 'Environment',
                                                'Value': 'Default'
                                            },
                                            {
                                            
                                                'Key': 'Application',
                                                'Value': 'Default'
                                            },
                                            {
                                            
                                                'Key': 'RetentionPeriod',
                                                'Value': '30'
                                            },
                                            {
                                            
                                                'Key': 'Owner',
                                                'Value': 'Default'
                                            },
                                            {
                                            
                                                'Key': 'Project',
                                                'Value': 'Default'
                                            },
                                            {
                                            
                                                'Key': 'Compliance',
                                                'Value': 'None'
                                            },
                                            {
                                            
                                                'Key': 'InstanceName',
                                                'Value': name
                                            }
                                            
                                        ]
                                    },
                                ]
                                )
                        #response is a dictionary containing ResponseMetadata and SnapshotId
                        status_code = response['ResponseMetadata']['HTTPStatusCode']
                        snapshot_id = response['SnapshotId']
                        # check if status_code was 200 or not to ensure the snapshot was created successfully
                        if status_code == 200:
                            write_csv_file(instanceId,rootVolumeId,rootDeviceName,snapshot_id,"Triggered","NA")
                        else:
                            write_csv_file(instanceId,rootVolumeId,rootDeviceName,snapshot_id,"Failed","error")
                    except:
                        error = PrintException()
                        write_csv_file(instanceId,rootVolumeId,rootDeviceName,snapshot_id,"Failed",error)
                    
                else:
                    write_csv_file(instanceId,rootVolumeId,rootDeviceName,snapshot_id,"Failed","Unable to find root volume name - /dev/sda1")
                    print("Cant find root volume(/dev/sda1)")
            if backup_requirement == "AMI":
                try:
                    print("Configured Backup type is AMI")
                    instanceId = instance['InstanceId']
                    ami_id = fetch_image_id(instanceId)
                    ami_name = 'Ft_Patch_Automation_' + instanceId + '_' + tagValue
                    ami_snapshot_name = 'AMI:Ft_Patch_Automation_' + instanceId
                    name = get_name_of_instance(instanceId)
                    response = ec2_client.create_image(
                        InstanceId=instanceId,
                        Name=ami_name,
                        NoReboot=True,
                        TagSpecifications=[
                            {
                                'ResourceType': 'image',
                                'Tags': [
                                    {
                                        'Key': 'InstanceName',
                                        'Value': name
                                    },
                                    {
                                        'Key': 'Environment',
                                        'Value': 'Default'
                                    },
                                    {
                                        'Key': 'encrypted',
                                        'Value': 'false'
                                    },
                                    {
                                        'Key': 'os',
                                        'Value': ''
                                    },
                                    {
                                        'Key': 'osservicelevel',
                                        'Value': 'GOLD'
                                    },
                                    {
                                        'Key': 'version',
                                        'Value': ''
                                    },
                                    {
                                        'Key': 'Original_AMI_ID',
                                        'Value': 'Created from ' + str(ami_id)
                                    },
                                ]
                            },

                            {
                                'ResourceType': 'snapshot',
                                'Tags': [
                                    {
                                        'Key': snapshotTagKey,
                                        'Value': ''
                                    },
                                    {
                                    
                                        'Key': 'Environment',
                                        'Value': ''
                                    },
                                    {
                                    
                                        'Key': 'Application',
                                        'Value': ''
                                    },
                                    {
                                    
                                        'Key': 'RetentionPeriod',
                                        'Value': ''
                                    },
                                    {
                                    
                                        'Key': 'Owner',
                                        'Value': ''
                                    },
                                    {
                                    
                                        'Key': 'Project',
                                        'Value': ''
                                    },
                                    {
                                    
                                        'Key': 'Compliance',
                                        'Value': ''
                                    },
                                    {
                                    
                                        'Key': 'InstanceName',
                                        'Value': name
                                    },
                                    {
                                    
                                        'Key': 'Name',
                                        'Value': ami_snapshot_name
                                    }
                            
                                ]
                            }
                        ]
                    )
        
                    Image_id = response['ImageId']
                    print("Image_id",Image_id)
                    status_code = response['ResponseMetadata']['HTTPStatusCode']
                    if status_code == 200:
                        write_csv_file(instanceId,'AMI',ami_name,Image_id,"Triggered","NA")
                except ClientError as err:
                    if err.response['Error']['Code'] == 'InvalidAMIName.Duplicate':
                        print(f"AMI Image - {ami_name} is already available and consider backup status of the instance {instanceId} is successful")
                        write_csv_file(instanceId,'AMI',ami_name,"","completed","Image is already exist. hence, skipped image creation and get old image id from ami name")
                    else:
                        print(PrintException())
                        write_csv_file(instanceId,'AMI',ami_name,Image_id,"Failed","error")
                    

    print("Instances are done")
        
def lambda_handler(event, context):
    global bucket_name
    global S3_directory_name
    global backupReport_Local_FullFileName
    global S3_Folder_Name,region,tagValue
    region = event['region']
    bucket_name = event['S3_Bucket']
    S3_directory_name = event['S3_directory_name']
    S3_Folder_Name = event['S3_Folder_Name']
    Patching_Type= event['Patching_Type']
    if Patching_Type == 'Adhoc':
        ssm_parameter = str(os.environ['AdhocBackupOptions'])
        tag_name = 'AdhocPatchInstallOn'
    else:
        ssm_parameter = str(os.environ['BackupOptions'])
        tag_name = 'PatchInstallOn'
                
    tagValue = event['PatchInstallOn']
    backupReportFileName = "Backup_Report_" + tagValue + ".csv"
    
    patchMonth = S3_directory_name.split("/")[0]
    region = S3_directory_name.split("/")[1]
    patchJobId = S3_directory_name.split("/")[2]
        
    backupReport_Local_Folder = "/tmp/"
    backupLogFolder = "/tmp/"
    backupReport_Local_FullFileName = backupReport_Local_Folder + backupReportFileName
    
    #S3
    backupReportS3Folder = S3_Folder_Name + "/" + 'PATCHING/' + S3_directory_name + '/Backup_Reports/'
    backupReportS3FileFullName = backupReportS3Folder + backupReportFileName
    
    call_update_dynamodb_lambda_function(patchJobId,attribute_name="backup_status",attribute_value="in progress")
    # update_item_dynamoDB(patchJobId,"backup_status","in progress")
    
    backup_type = read_ssm_parameter(ssm_parameter)
    if backup_type == "ROOTVOL":
        write_csv_file("InstanceId","RootVolumeID","DiskDeviceName","SnapshotId","Status","Comments")
    if backup_type == "AMI":
        write_csv_file("InstanceId","BackupType","AMI_Name","AMI_ID","Status","Comments")
    
    ec2_filter = [
                {'Name':"tag:"+tag_name, 'Values':[tagValue]}
                ]
    print("ec2 filter : ", ec2_filter)
    backup_root_volumes(tagValue,ec2_filter,ssm_parameter)
    
    if os.path.exists(backupReport_Local_FullFileName):
        upload_file_into_s3(backupReport_Local_FullFileName,backupReportS3FileFullName)
    
    count = 4 # WAIT time in Step Function is 15 minutes to check back again the snapshot status.
    #Hence, Count should be 4. Calculation or Logic here is, giving maximum one hour time to complete backups
    jsonValues = {}
    jsonValues['Patching_Type'] = Patching_Type
    jsonValues['PatchInstallOn'] = tagValue
    jsonValues['S3_Bucket'] = bucket_name
    jsonValues['S3_directory_name'] = S3_directory_name
    jsonValues['count'] = count
    jsonValues['S3_Folder_Name'] = S3_Folder_Name
    jsonValues['region'] = region
    print(jsonValues)
    return jsonValues
 
    
# simple test cases
if __name__ == "__main__":
    #event1 = {"Action": "enable"}
    event1 = {
  "S3_Bucket": "dxc",
  "S3_directory_name": "DEC_2021/ap-south-1/patchJobId_c096825b-5655-11ec-bdc0-3d9598f53224",
  "PatchInstallOn": "DEV-JUN_9_2022_13_30_4HRS",
  "S3_Folder_Name" : "Test",
  "region":"ca-central-1"
}

    lambda_handler(event1, "")

