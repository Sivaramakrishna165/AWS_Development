'''
This Lambda script creates CloudWatch Event rules for Install Patches, Patch Scanning and performing pre tasks.
It also creates EventBridge rules for Checking Change Request status is SNOW is enabled and checking patching window miss.
'''

import boto3
from botocore.client import Config
import json
import time
import sys
import datetime
import csv
import os
import sys
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))


client = boto3.client('events',config=config)
s3client = boto3.client('s3',config=config)
sfnclient = boto3.client('stepfunctions',config=config)
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

# StepFunRoleArn = "arn:aws:iam::338395754338:role/PatchingE2EAutomationCloudWatchRoleForSF"
# StepFunRoleArn = "arn:aws:iam::338395754338:role/DXC_PE2EA_IAM_StateMachineExecutionRole-ap-south-1"

# Sfnname_InstallPatch =  "DXC_PE2EA_SFN_TriggerPatching"
# StepFunArn_InstallPatch = "arn:aws:states:ap-south-1:338395754338:stateMachine:DXC_PE2EA_SFN_TriggerPatching"

# Sfnname_PatchScan =  "DXC_PE2EA_SFN_PatchScanReport"
# StepFunArn_PatchScan = "arn:aws:states:ap-south-1:338395754338:stateMachine:DXC_PE2EA_SFN_PatchScanReport"

# SfnArnPreTaskExecution = "arn:aws:states:ap-south-1:338395754338:stateMachine:DXC_PE2EA_SFN_PerformPreTasks"
# SfnNamePreTaskExecution = "DXC_PE2EA_SFN_PerformPreTasks"

# LF_ID_Snow_status_check = 'DXC_PE2EA_CheckCRStatus'
# LF_ARN_Snow_status_check = 'arn:aws:lambda:ap-south-1:338395754338:function:DXC_PE2EA_CheckCRStatus'


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

def read_jsonfile(S3_Bucket,S3_directory_name,Keyname1,Keyname2,Keyname3):    
    try:
        directory_name = S3_Folder_Name + "/" + "PATCHING" + "/" + S3_directory_name + "/" + "Patching_config.json"
        print("Reading Patching JSON config file : ", directory_name)
        response = s3client.get_object(Bucket=S3_Bucket, Key=directory_name)
        content = response['Body']
        jsonObject = json.loads(content.read())
        execute_patch_installation = jsonObject[Keyname1]
        execute_patch_scan = jsonObject[Keyname2] 
        Perform_pretasks = jsonObject[Keyname3]
        print("Perform_pretasks : ", Perform_pretasks)
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

def create_cloudwatchrule_patchscan(name,scheduleexpression,patch_Id,state):
    try:
        name = name + "_" + region
        response = client.put_rule(
            Name = name,
            EventPattern = json.dumps(scheduleexpression),
            State=state,
            Description='Cloudwatch rule for '+ name
        )
        attributeKeyName = "patch_job_status"
        attributeKeyValue = "scheduled"
        update_item_dynamoDB(patch_Id,attributeKeyName,attributeKeyValue)
        
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

    

def create_cloudWatchRules_for_patching(Tag_type,Patching_ype,S3_Bucket,S3_directory_name,Region,account_id):
    try:
        Execute_patch_installation, Execute_patch_scan, Perform_pretasks,patchConfigFullData = read_jsonfile(S3_Bucket,S3_directory_name,Keyname1,Keyname2,Keyname3)
     #   SfnArn,SfnRoleArn = fetch_StateMachineArn(SfnName)
     # CloudWatch Rules to Execute Patch Installation.
        for patchInstallName,patchInstallCornJobValue in Execute_patch_installation.items():
            print("patchConfigFullData : ", patchConfigFullData)
            target_key = patchInstallName.split("Install_Patch_")
            print(f"target Key is : {target_key}")
            print("patchJobIds => ", patchConfigFullData["patchJobIds"])
            patch_Id = patchConfigFullData["patchJobIds"][target_key[1]]
            print("Patch ID of Install Patch : ",patch_Id," - ",target_key[1])
            new_S3_directory_name = S3_directory_name + "/" + patch_Id
            Input_Val = {'Patching_Type': Tag_type,Patching_ype: str(target_key[1] + "_BY"),'S3_Bucket': str(S3_Bucket), 'S3_directory_name': str(new_S3_directory_name),'S3_Folder_Name': S3_Folder_Name , 'Action':'disable','region':region}
            patchInstallvalue = str("cron(" + patchInstallCornJobValue + ")")
            create_cloudwatchrule(patchInstallName,patchInstallvalue,patch_Id,state = "DISABLED")
            add_target_to_cloudwatchrule(patchInstallName,Input_Val,Sfnname_InstallPatch,StepFunArn_InstallPatch,StepFunRoleArn)
    # CloudWatch Rules to Execute Patch Scan
        for patchScanName,patchScanCronJobValue in Execute_patch_scan.items():
            target_key = patchScanName.split("PatchScan_")
            patch_Id = patchConfigFullData["patchJobIds"][target_key[1]]
            print("Patch ID of Patch Scan : ",patch_Id," - ",target_key[1])
            new_S3_directory_name = S3_directory_name + "/" + patch_Id
            input_val = {'Patching_Type': Tag_type,Patching_ype: str(target_key[1]),"Patch_Phase":"pre-patch","S3_Bucket": str(S3_Bucket), "S3_directory_name": str(new_S3_directory_name),'S3_Folder_Name': S3_Folder_Name,'region':region}
            patchScanCronValue = str("cron(" + patchScanCronJobValue + ")")
            state_machine_arn = 'arn:aws:states:'+Region+':'+account_id+':stateMachine:dxcms_pa_sfn_schedule_patching'
            rule_event_pattern = {
                'source': ['aws.states'],
                'detail-type': ['Step Functions Execution Status Change'],
                'detail': {
                    "status": ["SUCCEEDED"],
                    'stateMachineArn': [state_machine_arn]
                }
            }
            if Tag_type == 'Adhoc':
                create_cloudwatchrule_patchscan(patchScanName,rule_event_pattern,patch_Id,state = 'ENABLED')
                StepFunArn_PatchScan = 'arn:aws:states:'+Region+':'+account_id+':stateMachine:dxcms_pa_sfn_patch_scan_report-adhoc'
            else:
                create_cloudwatchrule(patchScanName,patchScanCronValue,patch_Id,state = 'ENABLED')
                StepFunArn_PatchScan = 'arn:aws:states:'+Region+':'+account_id+':stateMachine:dxcms_pa_sfn_patch_scan_report'
            add_target_to_cloudwatchrule(patchScanName,input_val,Sfnname_PatchScan,StepFunArn_PatchScan,StepFunRoleArn)
    # Cloudwatch Rules to Execute Backup
        for pretaskName,pretaskCronJobValue in Perform_pretasks.items(): 
            print("pretaskCronJobValue : ",pretaskCronJobValue, type(pretaskCronJobValue))
            #cron_expression = change_time(patchInstallCornJobValue,backup_trigger_time)
            target_key = pretaskName.split("Peform_PreTask_")
            patch_Id = patchConfigFullData["patchJobIds"][target_key[1]]
            print("Patch ID of Perform Pretask : ",patch_Id," - ",target_key[1])
            new_S3_directory_name = S3_directory_name + "/" + patch_Id
            input_value = {'Patching_Type': Tag_type,Patching_ype: str(target_key[1]),'S3_Bucket': str(S3_Bucket), 'S3_directory_name': str(new_S3_directory_name),'S3_Folder_Name': S3_Folder_Name,'region':region}
            #pretaskCronValue = str("cron(" + cron_expression + ")")
            pretaskCronValue = str("cron(" + pretaskCronJobValue + ")")
            create_cloudwatchrule(pretaskName,pretaskCronValue,patch_Id,state = 'ENABLED')
            add_target_to_cloudwatchrule(pretaskName,input_value,SfnNamePreTaskExecution,SfnArnPreTaskExecution,StepFunRoleArn)
            update_item_dynamoDB(patch_Id,"backup_state_status","scheduled")
    except:
        print(PrintException())


def create_SNOW_CWRule(tag_type,PW,Schedule_expression,TagValues,S3_Bucket,S3_directory_name,account_id):
    try: 
        month = S3_directory_name.split("/")[0]
        for tagvalue in TagValues:
            rule_name = "SNOW_CR_Status_Check_" + tagvalue
            response = client.put_rule(
                Name = rule_name,
                ScheduleExpression = Schedule_expression,
                State = 'ENABLED',
                Description='Cloudwatch rule for Service_now CR status check for tagvalue : ' + tagvalue
            )
            input_value = {"Patching_Type" : tag_type,"S3_Bucket" : S3_Bucket,"S3_directory_name" : S3_directory_name,"S3_Folder_Name": S3_Folder_Name, "region": region, "Tag_Value": tagvalue, "Trigger_Rule_Name": rule_name}
            if PW:
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
            else:
                lambdaTarget = client.put_targets(
                    Rule = rule_name,
                    Targets=[
                        {
                            'Id': str(LF_ID_Snow_status_check),
                            'Arn': str(LF_ARN_Snow_status_check),
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
    global bucket_name
    global S3_directory_name, S3_Folder_Name, region
    region = event['region']
    bucket_name = event['S3_Bucket']
    S3_directory_name = event['S3_directory_name']
    snow_integration = event['Snow_Integration_Status']
    S3_Folder_Name = event['S3_Folder_Name']
    TagValues = event['TagValues']
    TagName = event['TagName']
    account_id = boto3.client("sts").get_caller_identity()["Account"]
    if TagName == 'Downtime Window':
        patching_type = "PatchInstallOn"
        ScheduleExpression = "cron(00 09 * * ? *)"
        tag_type = 'Standard'
        pw=True
    else:
        patching_type = "PatchInstallOn"
        ScheduleExpression = "cron(00 * * * ? *)"
        tag_type = 'Adhoc'
        pw=False
    print("TagValues:",TagValues)
    #errorLogFolder = "C:\\temp\\"
    errorLogFolder = "/tmp/"
    errorLogFileName = "Error_Logs_Pre-Patching_" + 'CreateCloudWatchRules' + ".csv"
    errorLogFullFileName = errorLogFolder + errorLogFileName
    
    if (IsObjectExists(errorLogFullFileName)):
        download_file_from_S3_bucket(errorLogFileName)   
        
    if os.path.exists(errorLogFullFileName):
        print("File Exists")
        upload_file_into_s3(errorLogFullFileName,errorLogFileName)

    create_cloudWatchRules_for_patching(tag_type,patching_type,event['S3_Bucket'],event['S3_directory_name'],region,account_id)
    if snow_integration == 'ON':
        create_SNOW_CWRule(tag_type,pw,ScheduleExpression,TagValues,event['S3_Bucket'],event['S3_directory_name'],account_id)
    else:
        if TagName == 'Downtime Window': 
            create_check_pw_CWRule(TagValues,event['S3_Bucket'],event['S3_directory_name'],account_id)
        else:
            pass
    return event

# simple test cases
if __name__ == "__main__":
    event1 = {"S3_Bucket": "dxc","S3_directory_name": "NOV_2021/ap-south-1",'S3_Folder_Name': 'test','Snow_Integration_Status':'ON',"region":"ap-south-1"}   
    lambda_handler(event1, "")