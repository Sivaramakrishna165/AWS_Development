'''
This Lambda script generates patch scan report in CSV file format and store into 
S3 bucket and communicate the same to CloudOps team
'''

import boto3
import json
import time
import sys
import datetime
from datetime import datetime
import csv
import os
import copy
from botocore.errorfactory import ClientError
from botocore.client import Config
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))

def PrintException():
    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    captureErr = "Line No. : " + str(lineno)  + " | ERROR: " + str(exc_obj)
    return captureErr

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


# fetch Account_Id
def get_aws_account_info():
    accoundId = ""
    try:
        sts = boto3.client("sts",config=config)
        accoundId = sts.get_caller_identity()["Account"]    
    except:
        print(PrintException())
        accoundId = ""
    return accoundId

# fetch Account_Name for the Account_Id
def fetch_account_name():
    try:
        account_name = boto3.client('iam',config=config).list_account_aliases()['AccountAliases'][0]
    except: 
        print(PrintException())
        account_name = ""
    return account_name


#Fetch platform of Instance for the Tagvalue
def fetch_instance_platform(instanceId):
    try:
        ec2_client = boto3.client("ec2",region_name = region,config=config)
        platform = ""
        response = ec2_client.describe_instances(InstanceIds=[instanceId])

        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                try:
                    if instance['Platform'] == 'windows':
                        platform = "Windows"
                except:
                    platform = "Linux"
        return platform
    except:
        print(PrintException())

# fetch Instance_Name
def get_instance_name(Instance_id):
    # When given an instance ID as str e.g. 'i-1234567', return the instance 'Name' from the name tag.
    ec2 = boto3.resource('ec2',region_name = region)
    instancename = ''
    ec2instance = ec2.Instance(Instance_id)
    for tags in ec2instance.tags:
        if tags["Key"] == 'Name':
            instancename = tags["Value"]
    return instancename


def get_osname_instance(instance_id, inst_platform):
    ssm_client = boto3.client('ssm',region_name = region,config=config)
    #ssm_client = session.client('ssm',region_name=region)

    if inst_platform == "Linux":
        try:
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
        except:
            error = PrintException()
            print("ERROR : Unable to find OS - ", error)
            return error

    elif inst_platform == "Windows":
        try:
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
        except:
            error = PrintException()
            print("ERROR : Unable to find OS - ", error)
            return error
    else:
        return "Instance Platform Unknown"

def write_csv(csvFileName,Account_name,Instance_name,instanceId,Compliance_status,Critical_noncompliant_count,Security_noncompliant_count,Other_noncompliant_count,Critical_NonCompliant_Patch_Id,Security_NonCompliant_Patch_Id,Other_NonCompliant_Patch_Id,platform,os_name,Baseline_id):
    try:
        csv_file = csvFileName
        row_count = ''
        
        try:
            if csv_file == csvFileName:
                with open(csv_file,"r") as f:
                    reader = csv.reader(f,delimiter = ",")
                    data = list(reader)
                    row_count = len(data)
                    print("Rows present in csv file : ",row_count)
        except:
            row_count = 0
            print("Rows present in csv file : ",row_count)
        
        if csv_file == csvFileName:
            with open(csv_file, 'a',newline='') as resultFile:
                writer = csv.writer(resultFile)
                if row_count >= 1:
                    print("if part of the csv")
                    csv_columns = [['Account_Name','Instance name','Instance ID','Compliance status','Critical noncompliant count','Security noncompliant count','Other noncompliant count','Critical NonCompliant Patch_Id(KB)','Security NonCompliant Patch_Id(KB)','Other NonCompliant Patch_Id(KB)','Platform Type','Operation System','Baseline ID Used']]
                    row = [[Account_name,Instance_name,instanceId,Compliance_status,Critical_noncompliant_count,Security_noncompliant_count,Other_noncompliant_count,Critical_NonCompliant_Patch_Id,Security_NonCompliant_Patch_Id,Other_NonCompliant_Patch_Id,platform,os_name,Baseline_id]]
                    writer.writerows(row)
                else:
                    print("else part of csv")
                    csv_columns = [['Account_Name','Instance name','Instance ID','Compliance status','Critical noncompliant count','Security noncompliant count','Other noncompliant count','Critical NonCompliant Patch_Id(KB)','Security NonCompliant Patch_Id(KB)','Other NonCompliant Patch_Id(KB)','Platform Type','Operation System','Baseline ID Used']]
                    row = [[Account_name,Instance_name,instanceId,Compliance_status,Critical_noncompliant_count,Security_noncompliant_count,Other_noncompliant_count,Critical_NonCompliant_Patch_Id,Security_NonCompliant_Patch_Id,Other_NonCompliant_Patch_Id,platform,os_name,Baseline_id]]
                    writer.writerows(csv_columns)
                    writer.writerows(row)
    except:
        print(PrintException())


def list_compliance_report(Account_id,Account_name,instanceId,platform,instance_name,os_name,non_compliant_next_token,Compliance_status,Critical_noncompliant,Security_noncompliant,Other_noncompliant,Baseline_id):
    try:
        ssm_client = boto3.client('ssm',region_name = region,config=config)
        Instance_name = ''
        Operating_System_Name = ''

        if platform == "Windows":
            security_classification = "SecurityUpdates"
            critical_classification = "CriticalUpdates"
        else:
            security_classification = "Security"
            critical_classification = "Critical"

        Critical_noncompliant_count = 0
        Security_noncompliant_count = 0
        Other_noncompliant_count = 0
        
        
        if non_compliant_next_token == '' or non_compliant_next_token == None:   
            print("Non Complinat token is NONE")
            Critical_NonCompliant_Patch_Id = ''
            Security_NonCompliant_Patch_Id = ''
            Other_NonCompliant_Patch_Id = ''

            non_compliant_response = ssm_client.list_compliance_items(
            Filters=[
                {
                    'Key': 'Status',
                    'Values': [
                        'NON_COMPLIANT',
                    ],
                },
            ],
            ResourceIds=[
                instanceId,
            ],
            MaxResults = 50
                )
            try:
                non_compliant_next_token = non_compliant_response['NextToken']
                print("non_compliant_next_token : ",non_compliant_next_token)
            except:
                non_compliant_next_token == None
        else:
            print("Non Complinat token is NOT NONE")
            non_compliant_response = ssm_client.list_compliance_items(
                Filters=[
                    {
                        'Key': 'Status',
                        'Values': [
                            'NON_COMPLIANT',
                        ],
                    },
                ],
                ResourceIds=[
                    instanceId,
                ],
                NextToken = non_compliant_next_token,
                MaxResults = 50
                )
            try:
                non_compliant_next_token = non_compliant_response['NextToken']
            except:
                non_compliant_next_token = None

        print("non_compliant_next_token : ",non_compliant_next_token)


        if non_compliant_response['ComplianceItems'] == []:
            # Compliance_status.append('Compliant')
            compliant_response = ssm_client.list_compliance_items(
            Filters=[
                {
                    'Key': 'Status',
                    'Values': [
                        'COMPLIANT',
                    ],
                },
            ],
            ResourceIds=[
                instanceId,
            ],
            MaxResults = 50
            )
            if compliant_response['ComplianceItems'] == []:
                Compliance_status.append('NA')
            else :
                Compliance_status.append('Compliant')


            for item in compliant_response['ComplianceItems']:       
                if Baseline_id == "NA":
                    try:
                        Baseline_id = item['Details']['PatchBaselineId']
                    except:
                        print("")

        else:
            critical_noncompliant_patch_id_string = ''
            security_noncompliant_patch_id_string = ''
            other_noncompliant_patch_id_string = ''
            for item in non_compliant_response['ComplianceItems']: 
                Compliance_status.append('Non_Compliant')      
                try:
                    if item['Details']['Classification'] == critical_classification:
                        patch_id = item["Id"]
                        try:
                            CVE_id = item['Details']['CVEIds']
                        except:
                            CVE_id = ""
                        if CVE_id != "":
                            patch_id = str(patch_id) + " ( "+ str( CVE_id ) + ")"
                        else:
                            patch_id = str(patch_id)
                        Critical_noncompliant.append(str(patch_id))
                        Compliance_status.append('Non_Compliant')
                    if item['Details']['Classification'] == security_classification:
                        patch_id = item["Id"]
                        try:
                            CVE_id = item['Details']['CVEIds']
                        except:
                            CVE_id = ""
                        if CVE_id != "":
                            patch_id = str(patch_id) + " ( "+ str( CVE_id ) + ")"
                        else:
                            patch_id = str(patch_id)
                        Security_noncompliant.append(str(patch_id))
                        Compliance_status.append('Non_Compliant')
                    if item['Details']['Classification'] != security_classification and item['Details']['Classification'] != critical_classification:
                        patch_id = item["Id"]
                        try:
                            CVE_id = item['Details']['CVEIds']
                        except:
                            CVE_id = ""
                        if CVE_id != "":
                            patch_id = str(patch_id) + " ( "+ str( CVE_id ) + ")"
                        else:
                            patch_id = str(patch_id)
                        Other_noncompliant.append(str(patch_id))
                        Compliance_status.append('Non_Compliant')
                except:
                    print("there is no classification and PatchState")
                    Compliance_status.append('NA')

                if Baseline_id == "NA":
                    try:
                        Baseline_id = item['Details']['PatchBaselineId']
                    except:
                        print("")

            Critical_noncompliant_count = len(Critical_noncompliant)
            print("Critical Patch count : ",Critical_noncompliant_count)

            Security_noncompliant_count = len(Security_noncompliant)
            print("Security Patch count : ",Security_noncompliant_count)

            Other_noncompliant_count = len(Other_noncompliant)
            print("Other_noncompliant Patch count : ",Other_noncompliant_count)

            if len(Critical_noncompliant) > 1 :
                Critical_NonCompliant_Patch_Id = critical_noncompliant_patch_id_string.join([str((elem)+"\n") for elem in Critical_noncompliant])
            if len(Critical_noncompliant) == 0 :
                Critical_NonCompliant_Patch_Id = ''
            if len(Critical_noncompliant) == 1 :
                Critical_NonCompliant_Patch_Id = Critical_noncompliant[0]
            if len(Security_noncompliant) > 1 :
                Security_NonCompliant_Patch_Id = security_noncompliant_patch_id_string.join([str((elem)+"\n") for elem in Security_noncompliant ])
            if len(Security_noncompliant) == 0 :
                Security_NonCompliant_Patch_Id = ''
            if len(Security_noncompliant) == 1 :
                Security_NonCompliant_Patch_Id = Security_noncompliant[0]
            if len(Other_noncompliant) > 1 :
                Other_NonCompliant_Patch_Id = other_noncompliant_patch_id_string.join([str((elem)+"\n") for elem in Other_noncompliant ])
            if len(Other_noncompliant) == 0 :
                Other_NonCompliant_Patch_Id = ''
            if len(Other_noncompliant) == 1 :
                Other_NonCompliant_Patch_Id = Other_noncompliant[0]
        
        if non_compliant_next_token == '' or non_compliant_next_token == None:
            if 'Non_Compliant' in Compliance_status:
                Compliance_status_str = "Non Compliant"
            if 'NA' in Compliance_status:
                Compliance_status_str = "NA"
            if 'Compliant' in Compliance_status:
                Compliance_status_str = "Compliant"

            print("Compliant Status Str : ",Compliance_status_str)
            print("========================================================")
            # print("csvFileName ==> ",csvFileName," data-type = ",type(csvFileName))
            print("Account_name ==> ",Account_name," data-type = ",type(Account_name))
            print("instance_name ==> ",instance_name," data-type = ",type(instance_name))
            print("instanceId ==> ",instanceId," data-type = ",type(instanceId))
            print("Compliance_status_str ==> ",Compliance_status_str," data-type = ",type(Compliance_status_str))
            print("Critical_noncompliant_count ==> ",Critical_noncompliant_count," data-type = ",type(Critical_noncompliant_count))
            print("Security_noncompliant_count ==> ",Security_noncompliant_count," data-type = ",type(Security_noncompliant_count))
            print("Other_noncompliant_count ==> ",Other_noncompliant_count," data-type = ",type(Other_noncompliant_count))
            print("Critical_NonCompliant_Patch_Id ==> ",Critical_NonCompliant_Patch_Id," data-type = ",type(Critical_NonCompliant_Patch_Id))
            print("Security_NonCompliant_Patch_Id ==> ",Security_NonCompliant_Patch_Id," data-type = ",type(Security_NonCompliant_Patch_Id))
            print("Other_NonCompliant_Patch_Id ==> ",Other_NonCompliant_Patch_Id," data-type = ",type(Other_NonCompliant_Patch_Id))
            print("platform ==> ",platform," data-type = ",type(platform))
            print("os_name ==> ",os_name," data-type = ",type(os_name))
            print("Baseline_id ==> ",Baseline_id," data-type = ",type(Baseline_id))
            print("========================================================")

        else:
            Account_name,instance_name,instanceId,Compliance_status_str,Critical_noncompliant_count,Security_noncompliant_count,Other_noncompliant_count,Critical_NonCompliant_Patch_Id,Security_NonCompliant_Patch_Id,Other_NonCompliant_Patch_Id,platform,os_name,Baseline_id = list_compliance_report(Account_id,Account_name,instanceId,platform,instance_name,os_name,non_compliant_next_token,Compliance_status,Critical_noncompliant,Security_noncompliant,Other_noncompliant,Baseline_id)
        
        return Account_name,instance_name,instanceId,Compliance_status_str,Critical_noncompliant_count,Security_noncompliant_count,Other_noncompliant_count,Critical_NonCompliant_Patch_Id,Security_NonCompliant_Patch_Id,Other_NonCompliant_Patch_Id,platform,os_name,Baseline_id

    except:
        print(PrintException())       


#def main():
def lambda_handler(event,context):     
    try:
        global S3_Folder_Name,region
        now = datetime.now()
        current_time = now.strftime("%H:%M:%S")
        print("Current Time =", current_time)
        time_1 = datetime.strptime(current_time,"%H:%M:%S")
        region = event['region']
        s3 = boto3.client('s3',config=config)   
        s3_resource = boto3.resource('s3', config=Config(signature_version='s3v4'))
        patchCheckSumFile = {"completedServers":[]};
            
        #tagValue = event['PatchInstallOn']
        TagName = event['TagName']
        tagValues = event['TagValues']
        print("Tag Value : ", tagValues)
        bucket_name = event['S3_Bucket']
        directory_name = event['S3_directory_name']
        return_directory_name = event['S3_directory_name']
        S3_Folder_Name = event['S3_Folder_Name']                  
        #commandId = event['CommandId']
        bucket = s3_resource.Bucket(bucket_name)
        

        localFolder = "/tmp/"
        
        accountId = get_aws_account_info()
        account_name = fetch_account_name()

        for tagValue in tagValues:

            patchReportCSV = "PatchScanReport_" + tagValue + ".csv"
                    
            local_folder_patchCheckSum = localFolder + 'Schedulephase_PatchCheckSum_' + tagValue + '.json'

            patchCheckSum_fileName = 'Schedulephase_PatchCheckSum_' + tagValue + '.json'
            s3Key_patchCheckSum = S3_Folder_Name + "/" + "PATCHING/" + directory_name + "/CheckSumFiles/" + patchCheckSum_fileName
                                
            patchReportCSV_Local_Folder = localFolder + patchReportCSV
            
            #Download CheckSum file from S3
            try:
                #patchCheckSumFile = "/tmp/instances.json"
                patchCheckSumFile = localFolder + "instances.json"
                print("s3Key_patchCheckSum - S3 folder : ",s3Key_patchCheckSum)
                s3.download_file(bucket_name, s3Key_patchCheckSum, patchCheckSumFile)
                with open(patchCheckSumFile) as file:
                    patchCheckSumDict = json.load(file)
            except:
                print(PrintException())
                #sys.exit()

            serverListDirectory = directory_name + "/" + patchCheckSumDict["patchJob_id"]
            s3Key_patchScanReport = S3_Folder_Name + "/" + "PATCHING/" + serverListDirectory + "/ServersList/" + patchReportCSV
            print("BUCKET NAME : ",bucket_name)
            print(s3Key_patchCheckSum)
            print(patchCheckSum_fileName)
            
            patchCheckSumDictTemp = copy.deepcopy(patchCheckSumDict)
            
            if patchCheckSumDict["status"] == "pending":
                if path_exists(s3Key_patchScanReport,bucket_name):
                    try:
                        s3.download_file(bucket_name, s3Key_patchScanReport, patchReportCSV_Local_Folder)
                        time.sleep(5)
                    except:
                        print(PrintException())
                    
                for instanceId in patchCheckSumDictTemp["pendingServers"]:
                    print("************** :     " , patchCheckSumDict["pendingServers"])
                    print("Starting task for Instance ID : ", instanceId)

                    platform = fetch_instance_platform(instanceId)
                    instance_name = get_instance_name(instanceId)
                    os_name = get_osname_instance(instanceId,platform)

                    Account_name,instance_name,instanceId,Compliance_status_str,Critical_noncompliant_count,Security_noncompliant_count,Other_noncompliant_count,Critical_NonCompliant_Patch_Id,Security_NonCompliant_Patch_Id,Other_NonCompliant_Patch_Id,platform,os_name,Baseline_id = list_compliance_report(accountId,account_name,instanceId,platform,instance_name,os_name,None,[],[],[],[],'NA')
                    #print("result : ",result)
                    write_csv(patchReportCSV_Local_Folder,Account_name,instance_name,instanceId,Compliance_status_str,Critical_noncompliant_count,Security_noncompliant_count,Other_noncompliant_count,Critical_NonCompliant_Patch_Id,Security_NonCompliant_Patch_Id,Other_NonCompliant_Patch_Id,platform,os_name,Baseline_id)
                    
                    x = 0
                    for pendingServer in patchCheckSumDict["pendingServers"]:
                        if pendingServer == instanceId:
                            print("")
                            patchCheckSumDict["pendingServers"].pop(x)
                        x = x + 1
                    

                    now1 = datetime.now()
                    current_time1 = now1.strftime("%H:%M:%S")
                    print("Current Time 1 =", current_time1)
                    time_2 = datetime.strptime(current_time1,"%H:%M:%S")

                    time_interval = time_2 - time_1
                    diff_minutes = str(time_interval).split(":")[1]
                    print("Difference Minutes : ", diff_minutes)

                    if int(diff_minutes) > 12:
                        print("12 Minutes completed. Hence, uploading file to S3")
                        if local_folder_patchCheckSum == '/tmp/Schedulephase_PatchCheckSum_' + tagValue + '.json':
                            with open(local_folder_patchCheckSum, 'w') as outfile:
                                json.dump(patchCheckSumDict, outfile)
                            #Upload Patch Check Sum file to S3
                            bucket.upload_file(local_folder_patchCheckSum, s3Key_patchCheckSum)
                            #Upload Patch Scan Report to S3
                            bucket.upload_file(patchReportCSV_Local_Folder, s3Key_patchScanReport)
                            time.sleep(600)


                patchCheckSumDict["status"] = "completed"
                print("Data in check sum : ", patchCheckSumDict)
                
                if local_folder_patchCheckSum == '/tmp/Schedulephase_PatchCheckSum_' + tagValue + '.json':
                    with open(local_folder_patchCheckSum, 'w') as outfile:
                        json.dump(patchCheckSumDict, outfile)
                    #Upload Patch Check Sum file to S3
                    bucket.upload_file(local_folder_patchCheckSum, s3Key_patchCheckSum)
                    #Upload Patch Scan Report to S3
                    print("patchReportCSV_Local_Folder : ", patchReportCSV_Local_Folder)
                    print("s3Key_patchScanReport : ",s3Key_patchScanReport)
                    bucket.upload_file(patchReportCSV_Local_Folder, s3Key_patchScanReport)

        print("======================================================\n")
        print("Script Finished")
        jsonTagValues = {}
        jsonTagValues['TagName'] = TagName
        jsonTagValues['TagValues'] = tagValues
        jsonTagValues['S3_Bucket'] = bucket_name
        jsonTagValues['S3_directory_name'] = return_directory_name
        jsonTagValues['File_prefix'] = "PatchServerList"
        jsonTagValues['S3_Folder_Name'] = S3_Folder_Name
        jsonTagValues['region'] = region
        if 'OldTagValues' in event.keys():
            jsonTagValues['OldTagValues'] = event['OldTagValues']
            jsonTagValues['TagMapping'] = event['TagMapping']
        print(jsonTagValues)
        return jsonTagValues

    except:
        print(PrintException())
        
        

if __name__ == "__main__":
    # event1 = {"TagValues": ["DEV-JUL_25_2021_14_0_5HRS","DEV-JUL_24_2021_6_0_3HRS"],"S3_Bucket": "dxc","S3_directory_name": "JUL_2021/ap-south-1"}
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
