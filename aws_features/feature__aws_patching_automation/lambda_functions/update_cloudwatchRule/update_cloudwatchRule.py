'''
This Lambda script creates CloudWatch Event rules for Install Patches, Patch Scanning and performing pre tasks for the rescheduled tags.
And deleted CW rules for the old tags.
'''

import boto3
from botocore.client import Config
import json
import time
import sys
import datetime
import csv
import os
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))


client = boto3.client('events',config=config)
s3client = boto3.client('s3',config=config)
lambda_client = boto3.client('lambda',config=config)

region = os.environ['AWS_REGION']
StepFunRoleArn = os.environ['StepFunRoleArn']

Sfnname_InstallPatch =  os.environ['Sfnname_InstallPatch']
StepFunArn_InstallPatch = os.environ['StepFunArn_InstallPatch']

Sfnname_PatchScan =  os.environ['Sfnname_PatchScan']
StepFunArn_PatchScan = os.environ['StepFunArn_PatchScan']

SfnArnPreTaskExecution = os.environ['SfnArnPreTaskExecution']
SfnNamePreTaskExecution = os.environ['SfnNamePreTaskExecution']

LF_ID_Snow_status_check = os.environ['Service_now_status_check']
LF_ARN_Snow_status_check = os.environ['Service_now_status_check_Arn']

LF_ID_pw_status_check = os.environ['PatchingWindow_status_check'] #'dxcms-pa-lam-check-pw-status'
LF_ARN_pw_status_check = os.environ['PatchingWindow_status_check_Arn'] #'arn:aws:lambda:eu-west-3:567529657087:function:dxcms-pa-lam-check-pw-status'

Keyname1 = "executePatchInstallation"
Keyname2 = "executepatchscan"
Keyname3 = "performPreTasks"




def PrintException():
    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    captureErr = "Line No. : " + str(lineno)  + " | ERROR: " + str(exc_obj)
    return captureErr

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
        
def create_itemData_dynamoDB(patchJob_id,attributeKey,attributeValue):
    try:
        dynamodb = boto3.resource('dynamodb')
        updateAttribute = "set " + attributeKey + "=:data"
        patch_table = dynamodb.Table('Ft_dxcms_patching_e2e_automation')        
        patch_table.update_item(
                Key={'patchJob_id': patchJob_id},
                UpdateExpression=updateAttribute,
                ExpressionAttributeValues={':data': attributeValue},
                ReturnValues="UPDATED_NEW"
                ) 
    except:
        print(PrintException())

def update_item_dynamoDB(patchJob_id,attributeKeyName,attributeKeyValue):
    try:
        dynamodb = boto3.resource('dynamodb')
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
 
def read_ssm_parameter(name):
    ssm_para_client = boto3.client('ssm',config=config)
    response = ssm_para_client.get_parameter(
        Name=name,
    )
    ssm_parameter = response['Parameter']
    ssm_parameter_value = ssm_parameter['Value']
    return ssm_parameter_value


def IsObjectExists(path):
    s3 = boto3.resource('s3')
    bucket = s3.Bucket(bucket_name)
    for object_summary in bucket.objects.filter(Prefix=path):
        return True
    return False
    
    
def upload_file_into_s3(errorLogFullFileName,errorLogFileName):
    try:
        print("File Name : ",errorLogFileName )
        s3_resource = boto3.resource('s3', config=Config(signature_version='s3v4'))
        bucket = s3_resource.Bucket(bucket_name)
        Key = S3_Folder_Name + "/" + 'PATCHING/' + S3_directory_name + '/' + errorLogFileName
        print("Key : ", Key)
        print("errorLogFullFileName : ",errorLogFullFileName)
        bucket.upload_file(errorLogFullFileName, Key)
    except:
        print(PrintException())

def download_file_from_S3_bucket(errorLogFileName):
    s3client = boto3.client('s3',config=config)
    try:
        Key = S3_Folder_Name + "/" + 'PATCHING/' + S3_directory_name + '/' + errorLogFileName
        fileName = '/tmp/' + errorLogFileName
        #fileName = 'c:\\temp\\' + errorLogFileName
        s3client.download_file(bucket_name, Key, fileName)
        return True
    except:
        print(PrintException())
        return False

def write_csv_file(opFileName,stepName,resource,errorMsg):
    print(opFileName)
    print(stepName)
    print(resource)
    print(errorMsg)
    try:
        with open(opFileName, 'a', newline='') as csvfile:
            filewriter = csv.writer(csvfile, delimiter=',')        
            filewriter.writerow([stepName,resource,errorMsg])
    except:
        print(PrintException())

def filter_json(TagValues,data):
    try:
        filtereddata = {}
        key_list  = list(data.keys())
        for key in key_list:
            for tag in TagValues:
                if tag in key:
                    filtereddata[key] = data[key]
        return filtereddata
    except:
        print(PrintException())

def read_jsonfile(TagValues,S3_Bucket,S3_directory_name):    
    try:
        directory_name = S3_Folder_Name + "/" + "PATCHING" + "/" + S3_directory_name + "/" + "Patching_config.json"
        print("Reading Patching JSON config file : ", directory_name)
        response = s3client.get_object(Bucket=S3_Bucket, Key=directory_name)
        content = response['Body']
        jsonObject = json.loads(content.read())
        execute_patch_installation = filter_json(TagValues,jsonObject[Keyname1]) 
        execute_patch_scan = filter_json(TagValues,jsonObject[Keyname2])
        Perform_pretasks = filter_json(TagValues,jsonObject[Keyname3])
        return execute_patch_installation, execute_patch_scan, Perform_pretasks,jsonObject
    except:
        print(PrintException())


def create_cloudwatchrule(name,scheduleexpression,patch_Id,state):
    try:
        name = name + "_" + region
        response = client.put_rule(
            Name = name,
            ScheduleExpression = scheduleexpression,
            State=state,
            Description='Cloudwatch rule for '+ name
        )
        attributeKeyName = "patch_job_status"
        attributeKeyValue = "scheduled"
        update_item_dynamoDB(patch_Id,attributeKeyName,attributeKeyValue)
        
    except:
        print(PrintException())
        
def fetch_targets_by_rule(CloudwatchRules):
    try:
        CloudwatchTargets = []
        for i in range(len(CloudwatchRules)):
            print("CloudwatchRules : ",CloudwatchRules[i])
            response = client.list_targets_by_rule(
                Rule = CloudwatchRules[i]
            )
            y = (response['Targets'])
            print("y ",y)
            res = [ sub['Id'] for sub in y]
            CloudwatchTargets.append(res)
        print("CloudwatchRules : ",CloudwatchRules)
        print("CloudwatchTargets : ",CloudwatchTargets)
        res_dic = {CloudwatchRules[i]: CloudwatchTargets[i] for i in range(len(CloudwatchRules))}
        print("res_dic : ",res_dic)
        return res_dic
    except:
        print(PrintException())


def delete_old_cloudWatchRules(OldTagValues,snow_enable_status):
    try:
        for tag in OldTagValues:
            CWrules = ["Install_Patch_" + tag + "_" + region, "PatchScan_" + tag + "_" + region , "Peform_PreTask_" + tag + "_" + region]
            if snow_enable_status == "ON": 
                CWrules.append("SNOW_CR_Status_Check_" + tag)
            else: 
                CWrules.append("Patching_Window_Check_" + tag)
            if CWrules == None or CWrules == "" or CWrules == []:
                print(f"no Cloud Watch rules found with tag value : {TagValues} . Hence, skipping execution...")
            else:
                Targets = fetch_targets_by_rule(CWrules)
                print("Targets : ",Targets)
            for key,value in Targets.items():
                print("in remove target loop : ",key," ",value)
                response = client.remove_targets(
                    Rule = key,
                    Ids = value
                )
            for i in range(len(CWrules)):
                print("in delete CW rule loop : ",CWrules[i])
                response = client.delete_rule(
                    Name = CWrules[i]
                )
    except:
        print(PrintException()) 


def add_target_to_cloudwatchrule(rule,input_value,ID,ARN,RoleArn):
    try:
        rule = rule + "_" + region
        lambdaTarget = client.put_targets(
            Rule = rule,
            Targets=[
                {
                    'Id': str(ID),
                    'Arn': str(ARN),
                    'RoleArn': str(RoleArn),
                    'Input': json.dumps(input_value)
                }
            ]
        )
    except:
        err = PrintException()
        print("ERROR : ", err)
        step = "add target to cloudwatch"
        resource = "cloudwatch_target " + ID
        write_csv_file(opFileName,step,resource,err)

    

def create_cloudWatchRules_for_patching(TagValues,S3_Bucket,S3_directory_name):
    try:
        Execute_patch_installation, Execute_patch_scan, Perform_pretasks, patchConfigFullData = read_jsonfile(TagValues,S3_Bucket,S3_directory_name)
     # CloudWatch Rules to Execute Patch Installation.
        for patchInstallName,patchInstallCornJobValue in Execute_patch_installation.items():
            print("patchConfigFullData : ", patchConfigFullData)
            target_key = patchInstallName.split("Install_Patch_")
            print(f"target Key is : {target_key}")
            print("patchJobIds => ", patchConfigFullData["patchJobIds"])
            patch_Id = patchConfigFullData["patchJobIds"][target_key[1]]
            print("Patch ID of Install Patch : ",patch_Id," - ",target_key[1])
            new_S3_directory_name = S3_directory_name + "/" + patch_Id
            Input_Val = {"PatchInstallOn": str(target_key[1] + "_BY"),'S3_Bucket': str(S3_Bucket), 'S3_directory_name': str(new_S3_directory_name),'S3_Folder_Name': S3_Folder_Name , 'Action':'disable','region':region}
            patchInstallvalue = str("cron(" + patchInstallCornJobValue + ")")
            create_cloudwatchrule(patchInstallName,patchInstallvalue,patch_Id,state = "DISABLED")
            add_target_to_cloudwatchrule(patchInstallName,Input_Val,Sfnname_InstallPatch,StepFunArn_InstallPatch,StepFunRoleArn)
    # CloudWatch Rules to Execute Patch Scan
        for patchScanName,patchScanCronJobValue in Execute_patch_scan.items():
            target_key = patchScanName.split("PatchScan_")
            patch_Id = patchConfigFullData["patchJobIds"][target_key[1]]
            print("Patch ID of Patch Scan : ",patch_Id," - ",target_key[1])
            new_S3_directory_name = S3_directory_name + "/" + patch_Id
            input_val = {"PatchInstallOn": str(target_key[1]),"Patch_Phase":"pre-patch","S3_Bucket": str(S3_Bucket), "S3_directory_name": str(new_S3_directory_name),'S3_Folder_Name': S3_Folder_Name,'region':region}
            patchScanCronValue = str("cron(" + patchScanCronJobValue + ")")
            create_cloudwatchrule(patchScanName,patchScanCronValue,patch_Id,state = 'ENABLED')
            add_target_to_cloudwatchrule(patchScanName,input_val,Sfnname_PatchScan,StepFunArn_PatchScan,StepFunRoleArn)
    # Cloudwatch Rules to Execute Backup
        for pretaskName,pretaskCronJobValue in Perform_pretasks.items(): 
            print("pretaskCronJobValue : ",pretaskCronJobValue, type(pretaskCronJobValue))
            target_key = pretaskName.split("Peform_PreTask_")
            patch_Id = patchConfigFullData["patchJobIds"][target_key[1]]
            print("Patch ID of Perform Pretask : ",patch_Id," - ",target_key[1])
            new_S3_directory_name = S3_directory_name + "/" + patch_Id
            input_value = {"PatchInstallOn": str(target_key[1]),'S3_Bucket': str(S3_Bucket), 'S3_directory_name': str(new_S3_directory_name),'S3_Folder_Name': S3_Folder_Name,'region':region}
            #pretaskCronValue = str("cron(" + cron_expression + ")")
            pretaskCronValue = str("cron(" + pretaskCronJobValue + ")")
            create_cloudwatchrule(pretaskName,pretaskCronValue,patch_Id,state = 'ENABLED')
            add_target_to_cloudwatchrule(pretaskName,input_value,SfnNamePreTaskExecution,SfnArnPreTaskExecution,StepFunRoleArn)
            update_item_dynamoDB(patch_Id,"backup_state_status","scheduled")
    except:
        print(PrintException())


def create_SNOW_CWRule(TagValues,S3_Bucket,S3_directory_name,account_id):
    try: 
        month = S3_directory_name.split("/")[0]
        for tagvalue in TagValues:
            rule_name = "SNOW_CR_Status_Check_" + tagvalue
            response = client.put_rule(
                Name = rule_name,
                ScheduleExpression = "cron(00 09 * * ? *)",
                State = 'ENABLED',
                Description='Cloudwatch rule for Service_now CR status check for tagvalue : ' + tagvalue
            )
            input_value = {"S3_Bucket" : S3_Bucket,"S3_directory_name" : S3_directory_name,"S3_Folder_Name": S3_Folder_Name, "region": region, "Tag_Value": tagvalue, "Trigger_Rule_Name": rule_name}
            lambdaTarget = client.put_targets(
                Rule = rule_name,
                Targets=[
                    {
                        'Id': str(LF_ID_Snow_status_check),
                        'Arn': str(LF_ARN_Snow_status_check),
                        'Input': json.dumps(input_value)
                    },
                    {
                        'Id': str(LF_ID_pw_status_check),
                        'Arn': str(LF_ARN_pw_status_check),
                        'Input': json.dumps(input_value)
                    }
                ]
            )
            response = lambda_client.add_permission(
                FunctionName=LF_ID_Snow_status_check,
                StatementId='Patching_'+tagvalue,
                Action='lambda:InvokeFunction',
                Principal='events.amazonaws.com',
                SourceArn='arn:aws:events:'+region+':'+account_id+':rule/'+rule_name
            )
            response_pw = lambda_client.add_permission(
                FunctionName=LF_ID_pw_status_check,
                StatementId='PatchingWindowCheck_'+tagvalue,
                Action='lambda:InvokeFunction',
                Principal='events.amazonaws.com',
                SourceArn='arn:aws:events:'+region+':'+account_id+':rule/'+rule_name
            )
    except:
        print(PrintException())
    
def create_check_pw_CWRule(TagValues,S3_Bucket,S3_directory_name,account_id):
    try:
        month = S3_directory_name.split("/")[0]
        for tagvalue in TagValues:
            rule_name = "Patching_Window_Check_" + tagvalue
            print(rule_name)
            response = client.put_rule(
                Name = rule_name,
                ScheduleExpression = "cron(00 09 * * ? *)",
                State = 'ENABLED',
                Description='Cloudwatch rule for checking Patching Window status for tagvalue : ' + tagvalue
            )
            input_value = {"S3_Bucket" : S3_Bucket,"S3_directory_name" : S3_directory_name,"S3_Folder_Name": S3_Folder_Name ,'region': region, "Tag_Value": tagvalue, "Trigger_Rule_Name": rule_name}
            lambdaTarget = client.put_targets(
                Rule = rule_name,
                Targets=[
                    {
                        'Id': str(LF_ID_pw_status_check),
                        'Arn': str(LF_ARN_pw_status_check),
                        'Input': json.dumps(input_value)
                    }
                ]
            )
            response = lambda_client.add_permission(
                FunctionName=LF_ID_pw_status_check,
                StatementId='PatchingWindowCheck_'+tagvalue,
                Action='lambda:InvokeFunction',
                Principal='events.amazonaws.com',
                SourceArn='arn:aws:events:'+region+':'+account_id+':rule/'+rule_name
            )
    except:
        print(PrintException())

def lambda_handler(event, context):
    global bucket_name, S3_directory_name, S3_Folder_Name, region
    region = event['region']
    bucket_name = event['S3_Bucket']
    S3_directory_name = event['S3_directory_name']
    snow_integration = event['Snow_Integration_Status']
    S3_Folder_Name = event['S3_Folder_Name']
    TagValues = event['TagValues']
    OldTagValues = event['OldTagValues']
    print("TagValues:",TagValues)

    errorLogFolder = "/tmp/"
    errorLogFileName = "Error_Logs_Pre-Patching_" + 'CreateCloudWatchRules' + ".csv"
    errorLogFullFileName = errorLogFolder + errorLogFileName
    
    if (IsObjectExists(errorLogFullFileName)):
        download_file_from_S3_bucket(errorLogFileName)   
        
    if os.path.exists(errorLogFullFileName):
        print("File Exists")
        upload_file_into_s3(errorLogFullFileName,errorLogFileName)
    
    #Create new CW rules
    create_cloudWatchRules_for_patching(TagValues,bucket_name, S3_directory_name)
    account_id = boto3.client("sts",config=config).get_caller_identity()["Account"]
    if snow_integration == 'ON':
        create_SNOW_CWRule(TagValues,bucket_name,S3_directory_name,account_id)
    else:
        create_check_pw_CWRule(TagValues,bucket_name,S3_directory_name,account_id)
    
    #Delete old CW rules
    delete_old_cloudWatchRules(OldTagValues,snow_integration)
    
    return event

# simple test cases
if __name__ == "__main__":
    event1 =  {
	"OldTagValues": {
		"DEV-JUN_30_2023_15_0_4HRS": "patchJobId_fa844949-1a3d-11ee-9a9b-d74ac618a13f",
		"PROD-JUN_30_2023_15_0_3HRS": "patchJobId_fba11e3d-1a3d-11ee-b948-d74ac618a13f"
	},
	"TagValues": ["DEV-JUN_30_2023_10_0_4HRS", "PROD-JUN_30_2023_10_0_3HRS"],
	"S3_Bucket": "dxcms.patchingautomation.567529657087.eu-west-3",
	"S3_directory_name": "JUN_2023/eu-west-3",
    "File_prefix": "PatchServerList",
	"S3_Folder_Name": "patching_reports",
	"region": "eu-west-3",
    "Snow_Integration_Status": "ON"
} 
    lambda_handler(event1, "")
