'''
This Lambda script is used to generate the server list based on the PatchInstallOn tag and communicate to CloudOps team
'''

import boto3
import time
import json
import csv
import os.path
import logging
from botocore.client import Config
import datetime
import ast
import sys
from botocore.errorfactory import ClientError
import copy
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))

input_parameters = {}

class JSONObject:
    """
    Generic class help read json object
    """
    def __init__(self, d):
        self.__dict__ = d

def PrintException():
    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    captureErr = "Line No. : " + str(lineno)  + " | ERROR: " + str(exc_obj)
    return captureErr
 
def getInstances(ec2_resource,instance):
    try:
        running_instances = ec2_resource.instances.filter(InstanceIds=[instance])
        ec2info = {}
        for instance in running_instances:
            name = ""
            partOfAsg = "False"
            ASG = ""
            if instance.tags is not None:
                for tag in instance.tags:
                    if 'Name' == tag['Key']:
                        name = tag['Value']
                    if 'aws:autoscaling:groupName' in tag['Key']:
                        partOfAsg = "True"
                        ASG = tag['Value']

            # Add instance info to a dictionary
            ec2info[instance.id] = {
                'Name': name,
                'Type': instance.instance_type,
                'partofAsg' : partOfAsg,
                'ASG' : ASG
        }
    except:
        print(PrintException())
    return ec2info

def getInstPlatform(ec2_client,instance):
    response = ec2_client.describe_instances(InstanceIds=[instance])
    inst_platform = {}

    for reservation in response["Reservations"]:
        for instance in reservation["Instances"]:
            try:
                inst_platform[instance["InstanceId"]] = instance['Platform']
            except:
                inst_platform[instance["InstanceId"]] = "linux"

    return inst_platform


def getSSMAgentInfo(ssm_client, instance_list):
    #returns the ssm agent information
    #instance_list has only list of running instances

    ssm_instances = []

    while(len(instance_list)/99 > 0):
        sub_instances = instance_list[0:99]
        instance_list = instance_list[99:]

        response = ssm_client.describe_instance_information(
            Filters=[{
                'Key': 'InstanceIds',
                'Values': sub_instances}])
        ssm_instances.extend(response['InstanceInformationList'])

    return ssm_instances


def get_osname_instance(ssm_client, instance_id, inst_platform):
    try:
        if instance_id:

            if inst_platform == "linux":
                cmd = 'cat /etc/os-release | head -n 1 | sed "s/NAME=//"'


                response = ssm_client.send_command(
                    InstanceIds=[
                        instance_id
                    ],
                    DocumentName="AWS-RunShellScript",
                    Parameters={
                        'commands': [
                            cmd
                        ]
                    },
                )

                time.sleep(8)
                command_id = response['Command']['CommandId']

                output = ssm_client.get_command_invocation(
                    CommandId=command_id,
                    InstanceId=instance_id,
                )

                command_status = output['Status']


                if command_status == 'Success':
                    r = json.dumps(output)
                    loaded_r = json.loads(r)
                    os_details = loaded_r['StandardOutputContent']

                    cmd_op = os_details.strip('\r').strip('\n').strip('"')
                    return cmd_op

                else:
                    cmd_op = ''
                    return cmd_op

            elif inst_platform == "windows":

                cmd = '(gwmi win32_operatingsystem).caption'

                response = ssm_client.send_command(
                    InstanceIds=[
                        instance_id
                    ],
                    DocumentName="AWS-RunPowerShellScript",
                    Parameters={
                        'commands': [
                            cmd
                        ]
                    },
                )
                
                time.sleep(8)
                command_id = response['Command']['CommandId']
                output = ssm_client.get_command_invocation(
                    CommandId=command_id,
                    InstanceId=instance_id,
                )


                command_status = output['Status']

                if command_status == 'Success':
                    r = json.dumps(output)
                    loaded_r = json.loads(r)
                    os_details = loaded_r['StandardOutputContent']

                    cmd_op = os_details.strip("\n").rstrip("\r")
                    return cmd_op

                else:
                    cmd_op = ''
                    return cmd_op
            else:
                return "Instance Platform Unknown"

        else:
            return "Instance Id Invalid"
    except:
        return "Error-Check SSM agent and Instance state"


def getBucketContents(s3_resource, instance_id, bucket_name, bucket_prefix, platform):
    print("In getBucketContents function")
    bucket = s3_resource.Bucket(bucket_name)

    scanned_output = ""

    for obj in bucket.objects.filter(Prefix=bucket_prefix):
        if obj.size:
            scanned_output = obj.get()['Body'].read().decode('utf-8')

    #scanned_updates_inst = {}
    scanned_updates = []
    commandDocument = input_parameters["commandDocuments"][platform]
    
    if platform == "windows":
        print("In Windows IF condtion")
        output_lines = scanned_output.split("\r\n")
        if commandDocument == "AWS-RunPatchBaseline":
            upload = False
            found_missing = False
            for line in output_lines:
                if found_missing == False:
                    if line.__contains__("MissingCount"):
                        missing_cnt = int(line.split(":")[1].strip())
                        found_missing = True
                        if missing_cnt == 0:
                            break
                else:
                    if line.__contains__("Scan found the following updates missing:"):
                        scanned_line = line.split("Scan found the following updates missing:")[1].strip()
                        scanned_updates = scanned_line.split()
                        break


    else:
        output_lines = scanned_output.split("\n")
        upload = False
        return_list = []
        for line in output_lines:
            formatted_line = line.split('[INFO]:')[-1].strip()
            if upload == True:
                if formatted_line.__contains__("Summary") == False:
                    continue
                formatted_line = formatted_line.split("Summary:")[1].strip()
                summary = ast.literal_eval(formatted_line)
                no_of_missing_patches = int(summary["Content"][0]["MissingCount"])
                if no_of_missing_patches > 0:
                    return_list.append(str(no_of_missing_patches))

                return return_list
                
            if formatted_line != "Start to upload patch compliance.":
                continue
            else:
                upload = True

    return scanned_updates


def getFormattedPrefix(patchScanOutputFolder,instanceId, commandId, platform):

    if platform == "windows":
        prefix = '{}/{}/{}/awsrunPowerShellScript/PatchWindows/'.format(patchScanOutputFolder, commandId, instanceId)
    else:
        prefix = '{}/{}/{}/awsrunShellScript/PatchLinux/'.format(patchScanOutputFolder, commandId, instanceId)
    print(">>>>>>>>>>>>>>>>>>>>>>>>>",prefix)
    return prefix


def getDocumentParameters(inst_platform):
    commandDocument = input_parameters["commandDocuments"][inst_platform]
    parameters = {}
    if commandDocument == "AWS-RunPatchBaseline":
        parameters["Operation"] = ["Scan"]
        parameters["RebootOption"] = ["NoReboot"]
    elif commandDocument == "AWS-InstallWindowsUpdates":
        parameters["Action"] = ['Scan']
        parameters["AllowReboot"] = ['False']
    return parameters
    
def writeToCSV(instance, instance_info, instance_os,inst_platform,rowCount):
    csv_colums = ['InstanceId', 'InstanceName', 'Flavour', 'OperatingSystem', 'InstanceType', 'IsPartOfASG', 'ASGName']
    csv_file = input_parameters["outputFileName"]

    try:
        with open(csv_file, 'a',newline='') as resultFile:
            if rowCount == 1:
                #csv_colums = ['InstanceId', 'InstanceName', 'OperatingSystem', 'InstanceType', 'IsPartOfASG', 'ASGName', 'Compliant', 'NumberOfMissingUpdates', 'ListOfMissingUpdates']
                writer = csv.DictWriter(resultFile, fieldnames=csv_colums)
                writer.writeheader()
            else:
                writer = csv.DictWriter(resultFile, fieldnames=csv_colums)
            
            platform = inst_platform[instance]
            print("PLATFORM : ", platform)

            writer.writerow({
                        'InstanceId': instance,
                        'InstanceName': instance_info[instance]['Name'],
                        'Flavour': platform,
                        'OperatingSystem': instance_os,
                        'InstanceType': instance_info[instance]['Type'],
                        'IsPartOfASG':instance_info[instance]['partofAsg'],
                        'ASGName':instance_info[instance]['ASG']
                    })
                        
    except:
        err = PrintException()
        print(err)

def path_exists(path, bucket_name):
    """Check to see if an object exists on S3"""
    s3 = boto3.resource('s3')
    try:
        s3.ObjectSummary(bucket_name=bucket_name, key=path).load()
    except ClientError as e:
        if e.response['Error']['Code'] == "404":
            return False
        else:
            raise e
    return True

#def main():
def lambda_handler(event,context): 
    global input_parameters
    global commandId
    global S3_Folder_Name
    global region
    region = event['region']
    #make clients and resources from session
    ec2_client = boto3.client('ec2',region_name = region,config=config)
    ssm_client = boto3.client('ssm',region_name = region,config=config)
    ec2_resource = boto3.resource('ec2',region_name = region)
    s3_resource = boto3.resource('s3', config=Config(signature_version='s3v4'))
    s3 = boto3.client('s3',config=config)   
    
    serverCheckSumFile = {"completedServers":[]};
    whenToUploadOutputs = 8
          
    tagValues = event['TagValues']
    print("Tag Value : ", tagValues)
    bucket_name = event['S3_Bucket']
    directory_name = event['S3_directory_name']
    return_directory_name = event['S3_directory_name']
    S3_Folder_Name = event['S3_Folder_Name']
    
    bucket = s3_resource.Bucket(bucket_name)
    
    # localFolder = "c:\\temp\\"
    localFolder = "/tmp/"
    
    for tagValue in tagValues:
        patchServerListCSV = "PatchServerList_" + tagValue + ".csv"
        patchServerListCSV_Local_Folder = localFolder + patchServerListCSV
        #patchServerListCSV_Local_Folder = "/tmp/" + patchServerListCSV
        input_parameters["outputFileName"] = patchServerListCSV_Local_Folder
        
        local_folder_serverCheckSum = localFolder + 'ServerCheckSum_' + tagValue + '.json'
        #local_folder_serverCheckSum = '/tmp/ServerCheckSum_' + tagValue + '.json'
        local_file_serverCheckSum = 'ServerCheckSum_' + tagValue + '.json'
        s3Key_serverCheckSum = S3_Folder_Name + "/" + "PATCHING/" + directory_name + "/CheckSumFiles/" + local_file_serverCheckSum
        #s3Key_serverCheckSum = "PATCHING/" + directory_name + "/" + "PatchCheckSum_APR_4_2021_14_0_4HRS.json"     
        
        #Download CheckSum file from S3
        try:
            #serverCheckSumFile = "/tmp/instances.json"
            serverCheckSumFile = localFolder + "instances.json"
            print("s3Key_serverCheckSum :" ,s3Key_serverCheckSum)
            print("serverCheckSumFile :" ,serverCheckSumFile)
            s3.download_file(bucket_name, s3Key_serverCheckSum, serverCheckSumFile)
            with open(serverCheckSumFile) as file:
                serverCheckSumDict = json.load(file)
        except:
            print(PrintException())
            #sys.exit()
        
        serverListDirectory = directory_name + "/" + serverCheckSumDict["patchJob_id"]
        s3Key_serverReport = S3_Folder_Name + "/" + "PATCHING/" + serverListDirectory + "/ServersList/" + patchServerListCSV
        print("BUCKET NAME : ",bucket_name)
        print(s3Key_serverCheckSum)
        print(local_file_serverCheckSum)
        
        tag_instance_list = {}
        running_instance_ids = []
        rowCount = 0
        serverCheckSumDictTemp = copy.deepcopy(serverCheckSumDict)
        whenToUpload = 0
        
        if serverCheckSumDict["status"] == "pending":
            if path_exists(s3Key_serverReport,bucket_name):
                rowCount = 3 # It should not be 0 as dont want to include header again in the output file.
                try:
                    s3.download_file(bucket_name, s3Key_serverReport, patchServerListCSV_Local_Folder)
                except:
                    print(PrintException())
                
            #pendingServers = ["i-0d5758a7ec1373272","i-06fc5bd182644bbd4","i-007dfc22cd94d44d6"]
            #for instance in pendingServers:
            for instance in serverCheckSumDictTemp["pendingServers"]:
                whenToUpload = whenToUpload + 1
                print("************** :     " , serverCheckSumDict["pendingServers"])
                print("Starting task for Instance ID : ", instance)
                try:        
                    tag_instance_list = getInstances(ec2_resource,instance)
                except Exception as e:
                    print(PrintException())
                
                instance_platform = {}
                try:
                    instance_platform = getInstPlatform(ec2_client,instance)
               
                    instance_info = {}
                
                    for key, value in tag_instance_list.items():
                        instance_info[key] = value
                        
                    instance_list = []

                    instance_os_dict = {}

                    inst_platform = instance_platform[instance]            
                    instance_os = get_osname_instance(ssm_client, instance, inst_platform)
                    scanned_updates_inst = {}

                    rowCount = rowCount + 1
                    writeToCSV(instance, instance_info, instance_os,instance_platform,rowCount)
                    
                    x = 0
                    for pendingServer in serverCheckSumDict["pendingServers"]:
                        if pendingServer == instance:
                            print("")
                            serverCheckSumDict["pendingServers"].pop(x)
                        x = x + 1
                    
                    allowed_path = '/tmp/ServerCheckSum_' + tagValue + '.json'
                    
                    if whenToUpload == whenToUploadOutputs and local_folder_serverCheckSum == allowed_path:
                        whenToUpload = 0
                        with open(local_folder_serverCheckSum, 'w') as outfile:
                            json.dump(serverCheckSumDict, outfile)
                        #Upload Patch Check Sum file to S3
                        bucket.upload_file(local_folder_serverCheckSum, s3Key_serverCheckSum)
                        #Upload Patch Scan Report to S3
                        bucket.upload_file(patchServerListCSV_Local_Folder, s3Key_serverReport)
                                        
                except:
                    err = PrintException()
                    print(err)


            serverCheckSumDict["status"] = "completed"
            print("Data in check sum : ", serverCheckSumDict)
            
            if local_folder_serverCheckSum == allowed_path:
                with open(local_folder_serverCheckSum, 'w') as outfile:
                    json.dump(serverCheckSumDict, outfile)
                #Upload Patch Check Sum file to S3
                bucket.upload_file(local_folder_serverCheckSum, s3Key_serverCheckSum)
                #Upload Patch Scan Report to S3
                print("patchServerListCSV_Local_Folder : ", patchServerListCSV_Local_Folder)
                print("s3Key_serverReport : ",s3Key_serverReport)
                bucket.upload_file(patchServerListCSV_Local_Folder, s3Key_serverReport)
            else:
                raise RuntimeError('Filepath falls outside the base directory')
                
    print("======================================================\n")
    print("Script Finished")

    event['File_prefix'] = "PatchServerList"
    print(event)
    return event

if __name__ == "__main__":
    #event1 = {'PatchInstallOn': 'APR_18_2021_14_30_4HRS','S3_Bucket': 'dxc', 'S3_directory_name': 'APR_2021','CommandId':'0bbf6a60-d25d-43fb-983f-49b758ff2d39'}
    #event1 = {'PatchInstallOn': 'APR_25_2021_14_0_4HRS','S3_Bucket': 'dxc', 'S3_directory_name': 'APR_2021','CommandId':'8532895e-0180-4ca0-8f4d-bcf049bdc08f'}
    event1 = {
  "TagValues": [
    'WIN_TEST-NOV_21_2021_13_30_4HRS'
  ],
  "S3_Bucket": "dxc",
  'S3_directory_name': 'NOV_2021/ap-south-1',
  'S3_Folder_Name': 'test',
  "region":"ap-south-1"
}
    lambda_handler(event1, "")
