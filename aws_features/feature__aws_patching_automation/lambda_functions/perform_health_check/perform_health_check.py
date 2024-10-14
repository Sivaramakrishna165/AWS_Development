'''
This lambda script is used to trigger low level health check scripts on instances using SSM command
'''

import boto3
import time,os
import re
import csv
import yaml
import sys
import json
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))

s3_client = boto3.client('s3',config=config)
s3_resource = boto3.resource('s3')
ssm_client_document = boto3.client('ssm',config=config)

SSM_CW_Log_Group = os.environ['SSM_CWLogGroup_Name']

snsRoleArn = os.environ['snsIAMRole']
snsTopicArn = os.environ['snsTopic']

# SSM_CW_Log_Group = '/aws/ssm/dxc_pa_ssm_stdout'
# snsTopicArn = 'arn:aws:sns:_ap-southeast-1:983727160443:dxc_pa_sns_check_health_status'
# snsRoleArn = 'arn:aws:iam::983727160443:role/dxc_pa_iam_sns_role_ap-southeast-1'


def PrintException():
    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    captureErr = "Line No. : " + str(lineno)  + " | ERROR: " + str(exc_obj)
    return captureErr

def get_data_from_yaml_file(S3_Bucket):
    try:
        S3_Key = S3_Folder_Name + "/" + "HealthCheckConfigAndScripts/ConfigFile/healthCheckConfig.yml"
        response = s3_client.get_object(Bucket=S3_Bucket, Key=S3_Key)
        try:
            configfile = yaml.safe_load(response["Body"])
            #print(configfile)
            Windows_patch_checks = configfile['Patch_Checks'][0]
            #platform_check = patch_checks['Check_Name']
            Windows_sub_check = Windows_patch_checks['Sub_Checks']
            Windows_check_name = [ sub['Name'] for sub in Windows_sub_check]
            Linux_patch_checks = configfile['Patch_Checks'][1]
            linux_sub_check = Linux_patch_checks['Sub_Checks']
            Linux_Check_Name = [ sub['Name'] for sub in linux_sub_check]
            return Windows_check_name, Linux_Check_Name
        #    Check_Name = [ sub['Name'] for sub in y]        
        except yaml.YAMLError as exc:
            print(exc)
    except:
        print(PrintException())        

def fetch_instance_ids(TagValues,Patching_tag):
    try:
        instanceCount = 0
        windows_instance_id = []
        linux_instance_id = []
        instanceTags = (TagValues + "*")
        response = ec2_client.describe_instances(
            Filters=[
                {
                    'Name': 'tag:'+Patching_tag,
                    'Values': [
                        instanceTags,
                    ]
                },
            ]
        )
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                instanceCount = instanceCount + 1
                try:
                    if instance['Platform'] == 'windows':
                        windows_instance_id.append(instance["InstanceId"])
                except:
                    linux_instance_id.append(instance["InstanceId"])
        return windows_instance_id,linux_instance_id,instanceCount
    except:
        print(PrintException())
'''
TagValues = 'APR_4_2021_14_0_4HRS'
TagValues = 'JUN_20_2021_14_0_4HRS'
x,y = fetch_instance_ids(TagValues)
print(x,y)
<bucketName>/PATCHING/<MON_YYYY>/Outputs/Pre_HealthCheck/
'''
def fetch_instance_status(instance_ids):
    try:
        response = ec2_client.describe_instance_status(
            Filters=[
            {
                'Name': 'instance-state-name',
                'Values': [
                    'running',
                ]
            },
        ],
            InstanceIds = instance_ids
        )  
        instance_status = response['InstanceStatuses']
        running_instance_ids = [ sub['InstanceId'] for sub in instance_status]
        return running_instance_ids
    except:
        print(PrintException())

# fetch the document hash value
def get_document_hash(document_name):
    try:
        response = ssm_client_document.describe_document(
            Name=document_name
        )
        hash_value = response['Document']['Hash']
    except Exception as e:
        hash_value = ''
    return hash_value

# S3_Bucket,S3_directory_name,instance_id,cmd,Phase,tagValue
def ssm_command_for_Windows(S3_Bucket,S3_directory_name,instance_id,cmd,health_ckeck,Phase,tagValue):
    try:
        #timeout Logic here is , assuming 5 minutes should be enough to complete execution of one low level script for one server. Hence, calculation is no. of Instance * 5 minutes
        S3_key = S3_Folder_Name + "/" + "PATCHING/" + S3_directory_name + "/Outputs/" + Phase + "_HealthCheck/"
        running_instance_ids = fetch_instance_status(instance_id)
        timeout = len(running_instance_ids) * 300
        # SSM_CW_Log_Group = "AWS_Patching_Automation/" + patchjobid
        document_hash = get_document_hash('AWS-RunPowerShellScript')
        response = ssm_client.send_command(
            InstanceIds=instance_id,
            DocumentName='AWS-RunPowerShellScript',
            DocumentVersion='1',
            DocumentHash=document_hash,
            DocumentHashType='Sha256',
            TimeoutSeconds=timeout,
            Comment='perform' + health_ckeck + 'health check on windows servers',
            OutputS3BucketName=S3_Bucket,
            OutputS3KeyPrefix=S3_key,
            Parameters={
                'commands': [
                    cmd,
                ]
            },
            MaxConcurrency='50%',
            MaxErrors='100%',
            ServiceRoleArn=snsRoleArn,
            NotificationConfig={
                'NotificationArn': snsTopicArn,
                'NotificationEvents': [
                        'Success','TimedOut','Cancelled','Failed',
                    ],
                'NotificationType': 'Command'
            },
            CloudWatchOutputConfig={
                'CloudWatchLogGroupName': SSM_CW_Log_Group,
                'CloudWatchOutputEnabled': True
            }
        )
        #time.sleep(2)
        command_id = response['Command']['CommandId']
        #time.sleep(20)
        #status = response['Command']['Status']
        #print(status)
        print(command_id)
        return command_id,instance_id
    except:
        print(PrintException())

def ssm_command_for_linux(S3_Bucket,S3_directory_name,instance_id,cmd,Phase,tagValue,health_ckeck):
    try:
        S3_key = S3_Folder_Name + "/" + "PATCHING/" + S3_directory_name + "/Outputs/" + Phase + "_HealthCheck/"
        running_instance_ids = fetch_instance_status(instance_id)
        timeout = len(running_instance_ids) * 300
        # SSM_CW_Log_Group = "AWS_Patching_Automation/" + patchjobid
        document_hash = get_document_hash('AWS-RunShellScript')
        response = ssm_client.send_command(
            InstanceIds=instance_id,
            DocumentName='AWS-RunShellScript',
            DocumentVersion='1',
            DocumentHash=document_hash,
            DocumentHashType='Sha256',
            TimeoutSeconds=timeout,
            Comment='perform ' + health_ckeck + ' health check on linux servers',
            OutputS3BucketName=S3_Bucket,
            OutputS3KeyPrefix=S3_key,
            Parameters={
                'commands': [
                    cmd,
                ]
            },
            MaxConcurrency='50%',
            MaxErrors='100%',
            ServiceRoleArn=snsRoleArn,
            NotificationConfig={
                'NotificationArn': snsTopicArn,
                'NotificationEvents': [
                        'Success','TimedOut','Cancelled','Failed',
                    ],
                'NotificationType': 'Command'
            },
            CloudWatchOutputConfig={
                'CloudWatchLogGroupName': SSM_CW_Log_Group,
                'CloudWatchOutputEnabled': True
            }
        )
        #time.sleep(5)
        command_id = response['Command']['CommandId']
        print(command_id)
        return command_id,instance_id
    except:
        print(PrintException())

# def fetch_output_from_s3(S3_Bucket,itemname):
#     try:
#         s3 = boto3.resource('s3')
#         obj = s3.Object(S3_Bucket, itemname)
#         body = obj.get()['Body'].read().decode("utf-8")
#         output = str(body)
#         #print(output)
#         return output
#     except:
#         print(PrintException())

# def fetch_output_from_CWlog_event(Command_id,instance_id,platform):
#     cw_log_client = boto3.client('logs')
#     if platform == 'Windows':
#         CW_log_stream_name = Command_id + "/" + instance_id + "/" + "aws-runPowerShellScript/stdout"
#     if platform == 'Linux':
#         CW_log_stream_name = Command_id + "/" + instance_id + "/" + "aws-runShellScript/stdout"
#     response = cw_log_client.get_log_events(
#         logGroupName = SSM_CW_Log_Group,
#         logStreamName= CW_log_stream_name,
#         startFromHead=True
#     )
#     cw_log_msg = response['events'][0]['message']
#     print("cw_log_msg : ",cw_log_msg)
#     return cw_log_msg

def generate_json_config_file(Command_Id,Instance_Id,Health_check,HC_SSM_CmdIds_ConfigFileName,Platform):
    try:
        Health_check_Config_File = {}
        data = {}
        data['command_id'] = ""
        data['Instance_id'] = ""
        data['health_Check'] = ""
        data['Platform'] = ""
        file = []
        for i in range(len(Command_Id)):
    #        for key,value in data.items():
            data['command_id'] = Command_Id[i]
            data['Instance_id'] = Instance_Id[i]
            data['health_Check'] = Health_check[i]
            data['Platform'] = Platform[i]
            data_copy = data.copy()
            file.append(data_copy)
        Health_check_Config_File = file
        # localFolder = 'c:\\temp\\Health_check_Config_File.json'
        localFolder = '/tmp/Health_check_Config_File.json'
#       with open('c:\\temp\\Health_check_Config_File.json', 'w') as outfile:
        with open(localFolder, 'w') as outfile:
            json.dump(Health_check_Config_File, outfile)
        bucket = s3_resource.Bucket(S3_Bucket)
        #S3Key_for_congif_file = "PATCHING/" + S3_directory_name + "/Health_Check_Config_File/" + "Health_Check_" + TagValues + ".json"
        bucket.upload_file(localFolder, HC_SSM_CmdIds_ConfigFileName)
        return Health_check_Config_File  
    except:
        print(PrintException())


def execute_windows_health_check(S3_Bucket,S3_directory_name,instance_id,Phase,tagValue):
    try:
        health_check,linux_health_check = get_data_from_yaml_file(S3_Bucket)
        print(health_check)
        print(instance_id)
        InstanceIds = []
        Health_Check = []
        Command_Id = []
        #instance_id,linux_instance_id = fetch_instance_ids(TagValues)
        s3 = boto3.resource('s3')
        for i in range(len(health_check)):
            cmd_path = S3_Folder_Name + "/" + "HealthCheckConfigAndScripts/LowLevelScripts/Windows/" + health_check[i] + ".ps1"
            obj = s3.Object(S3_Bucket,cmd_path)
            cmd = obj.get()['Body'].read().decode("utf-8")
            #print(cmd)
            command_id,instance_id = ssm_command_for_Windows(S3_Bucket,S3_directory_name,instance_id,cmd,Phase,tagValue,health_check[i])
            print(command_id,instance_id)
            Command_Id.append(command_id)
            InstanceIds.append(instance_id)
            Health_Check.append(health_check[i])
            #generate_config_file(Command_Id,InstanceIds,Health_Check,platform = 'Windows')
            '''
            if status == 'Success' or 'Pending':
                time.sleep(10)
                itemname = command_id + "/" + instance_id + "/awsrunPowerShellScript/0.awsrunPowerShellScript/stdout"
                print(itemname)
            '''
#               write_into_csv_file(S3_Bucket,S3_directory_name,health_check[i],instance_id,itemname,platform = "Windows")
        return(Command_Id,InstanceIds,Health_Check)
    except:
        print(PrintException())

def execute_linux_health_check(S3_Bucket,S3_directory_name,instance_id,Phase,tagValue):
    try:
        health_check,linux_health_check = get_data_from_yaml_file(S3_Bucket)
        print(health_check)
        print(instance_id)
        InstanceIds = []
        Health_Check = []
        Command_Id = []
        windows_health_check,health_check = get_data_from_yaml_file(S3_Bucket)
        #windows_instance_id,instance_id = fetch_instance_ids(TagValues)
        s3 = boto3.resource('s3')
        for i in range(len(health_check)):  
            cmd_path = S3_Folder_Name + "/" + "HealthCheckConfigAndScripts/LowLevelScripts/Linux/" + health_check[i] + ".sh"
            obj = s3.Object(S3_Bucket,cmd_path)            
            cmd = obj.get()['Body'].read().decode("utf-8")
            command_id,instance_id = ssm_command_for_linux(S3_Bucket,S3_directory_name,instance_id,cmd,Phase,tagValue,health_check[i])
            #time.sleep(10)
            Command_Id.append(command_id)
            InstanceIds.append(instance_id)
            Health_Check.append(health_check[i])
            #itemname = command_id + "/" + instance_id + "/awsrunShellScript/0.awsrunShellScript/stdout"
            #print(itemname)
#            write_into_csv_file(S3_Bucket,S3_directory_name,health_check[i],instance_id,itemname,platform = 'Linux')
        return(Command_Id,InstanceIds,Health_Check)
    except:
        print(PrintException())

def call_update_dynamodb_lambda_function(patchJob_id):
    lambda_client = boto3.client('lambda',config=config)
    dynamo_event = {'patchJob_id': patchJob_id,'attribute_name':'pre_health_check_status','attribute_value':'in-progress'}
    response = lambda_client.invoke(
        FunctionName='dxcms-pa-lam-update-dynamodb',
        Payload=json.dumps(dynamo_event)
    )

def get_aws_account_info():
    accoundId = ""
    try:
        sts = boto3.client("sts",config=config)
        accoundId = sts.get_caller_identity()["Account"]    
    except:
        print(PrintException())
        accoundId = ""
    return accoundId

def lambda_handler(event, context):
    try:
        global snsRoleArn 
        #snsRoleArn = 'arn:aws:iam::338395754338:role/DXC_PE2EA_IAM_SNSRole'
        # snsRoleArn = os.environ['snsIAMRole']
        # global snsTopicArn
        #snsTopicArn = 'arn:aws:sns:ap-south-1:338395754338:DXC_PE2EA_SNS_HealthCheckStatus'
        # snsTopicArn = os.environ['snsTopic']
        global TagValues,S3_Bucket,S3_directory_name,S3_Folder_Name,region,ssm_client,ec2_client,snsTopicArn,patchjobid
        region = event['region']
        patching_type = event['Patching_Type']
        if patching_type == 'Standard':
            patching_tag = "PatchInstallOn"
        else:
            patching_tag = "AdhocPatchInstallOn"
        TagValues = event['PatchInstallOn']
        S3_Bucket = event['S3_Bucket']
        S3_directory_name = event['S3_directory_name']
        S3_Folder_Name = event['S3_Folder_Name']

        patchjobid = S3_directory_name.split('/')[2]
        commandIdConfigFile = {}
        totalCommandIdCount = 0

        account_id = get_aws_account_info()
        snsTopicArn = "arn:aws:sns:" + region + ":" + account_id + ":dxcms_pa_sns_check_health_status"

        ssm_client = boto3.client('ssm',region_name = region,config=config)
        ec2_client = boto3.client('ec2',region_name = region,config=config)
        
        Phase = event['Phase']
        
        TagValues = TagValues.split("_BY")[0]
                    
        if Phase == "post":
            tagValue_for_run_cmd = TagValues + "_BY_AY"
            print("Passed Tag Value is : ", TagValues)
            print("Tag Value for RUN command : ", tagValue_for_run_cmd)
            HC_SSM_CmdIds_ConfigFileName = S3_Folder_Name + "/" + "PATCHING/" + S3_directory_name + "/HealthCheck_SSM_CommandIDs/" + "post_HC_SSM_CommandIDs_" + TagValues + ".json"
        if Phase == "pre":
            tagValue_for_run_cmd = TagValues
            print("Passed Tag Value is : ", TagValues)
            print("Tag Value for RUN command : ", tagValue_for_run_cmd)
            HC_SSM_CmdIds_ConfigFileName = S3_Folder_Name + "/" + "PATCHING/" + S3_directory_name + "/HealthCheck_SSM_CommandIDs/" + "pre_HC_SSM_CommandIDs_" + TagValues + ".json"
            
        windows_instance_id,linux_instance_id,instanceCount = fetch_instance_ids(TagValues,patching_tag)
        print(windows_instance_id,linux_instance_id)
        config_file_Command_ids = []
        config_file_Instance_ids = []
        config_file_Health_check = []
        config_file_Platform = []
        if len(windows_instance_id) > 0:
            Command_Id,InstanceIds,Health_Check = execute_windows_health_check(S3_Bucket,S3_directory_name,windows_instance_id,Phase,tagValue_for_run_cmd)
            print("InstanceIds : ",InstanceIds)
            for i in range(len(Command_Id)):
                config_file_Command_ids.append(Command_Id[i])
                config_file_Instance_ids.append(InstanceIds[i])
                config_file_Health_check.append(Health_Check[i])
                config_file_Platform.append("Windows")
            #Window_config_file = generate_json_config_file(Command_Id,InstanceIds,Health_Check,HC_SSM_CmdIds_ConfigFileName,Platform ="Windows")
        if len(linux_instance_id) > 0:
            Command_Id,InstanceIds,Health_Check = execute_linux_health_check(S3_Bucket,S3_directory_name,linux_instance_id,Phase,tagValue_for_run_cmd)
            for i in range(len(Command_Id)):
                config_file_Command_ids.append(Command_Id[i])
                config_file_Instance_ids.append(InstanceIds[i])
                config_file_Health_check.append(Health_Check[i])
                config_file_Platform.append("Linux")
            #Linux_config_file = generate_json_config_file(Command_Id,InstanceIds,Health_Check,HC_SSM_CmdIds_ConfigFileName,Platform ="Linux"        
        print(config_file_Command_ids)
        print(config_file_Instance_ids)
        print(config_file_Health_check)
        print(config_file_Platform)
        HC_Config_File = generate_json_config_file(config_file_Command_ids,config_file_Instance_ids,config_file_Health_check,HC_SSM_CmdIds_ConfigFileName,config_file_Platform)
        print("config_file_Platform : ",HC_Config_File)
       
        #Assuming 5 minutes will be taken for each server to complete health check. Hence, here getting totalExecutionMinutes by multiplying total Instances X 5 minutes.
        #Command IDs count will be differ based on the Health Check Low Level Scrtips. But Low level scripts will be executed parallely for all the instances, not considering the count of Command IDs. However, just for giving additional time, we are multiplying total execution time into 2 [ totalExecutionMinutes X 2 ]
        totalExecutionMinutes =  int(instanceCount) * 5 
        totalExecutionMinutes = totalExecutionMinutes * 2
        
        # WAIT time should be 10 minutes. Hence, checking how many 10 minutes are in totalExecutionMinutes to find value of COUNT
        count = (totalExecutionMinutes / 10)
        
        # splited_patchJobId = S3_directory_name.split("/")
        # patch_job_id = splited_patchJobId[2]
        # call_update_dynamodb_lambda_function(patch_job_id)

        output = {}
        output['Patching_Type'] = patching_type
        output['Status'] = 'pending'
        output['Count'] = count
        output['PatchInstallOn'] = TagValues
        output['S3_Bucket'] = S3_Bucket
        output['S3_directory_name'] = S3_directory_name
        output['Phase'] = Phase
        output['S3_Folder_Name'] = S3_Folder_Name
        output['region'] = region
        return output
    except:
        print(PrintException())


if __name__ == "__main__":
    event1 = {
        "Phase": "pre",
        "PatchInstallOn":"RHEL_TEST-MAY_8_2022_13_30_4HRS",
        "S3_Bucket": "dxc",
        "S3_directory_name": "NOV_2021/ap-south-1/patchJobId_90963df6-46b9-11ec-b2db-8c8caa2990d1",
        # 'S3_directory_name': 'PATCHING',
        "S3_Folder_Name": "test",
        "region": "ap-south-1"
    }

    lambda_handler(event1, "")