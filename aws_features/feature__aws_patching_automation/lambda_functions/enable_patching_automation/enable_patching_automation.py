'''
This Lambda script is used to enable patching automation. 
User has to execute this manually to enable this entire patching automation solution.
'''

import boto3
import sys
import os
import json,time
import botocore
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))

Patching_Type = os.environ['Patching_Type']

region = os.environ['AWS_REGION']
CloudOps_Email_IDs = os.environ['cloudOpsEmailId']
CloudOps_Teams_Channel = os.environ['cloudOpsTeamsChannel']
Sender_Email_ID = os.environ['SenderEmailId']

StepFunRoleArn = os.environ['StepFunRoleArn']
Sfnname = os.environ['Sfnname']
StepFunArn = os.environ['StepFunArn']

# Sfnname = 'DXC_PE2EA_SFN_SchedulePatching'
# StepFunArn = 'arn:aws:states:ap-south-1:338395754338:stateMachine:DXC_PE2EA_SFN_SchedulePatching'
# StepFunRoleArn = 'arn:aws:iam::338395754338:role/DXC_PE2EA_IAM_StateMachineExecutionRole-ap-south-1'

SNS_Topics = ['dxcms_pa_sns_notify_patch_failure','dxcms_pa_sns_reboot_dependent_instance_01','dxcms_pa_sns_reboot_dependent_instance_02','dxcms_pa_sns_reboot_dependent_instance_03','dxcms_pa_sns_app_notify_failure','dxcms_pa_sns_check_health_status']
SNS_Subscriptions = ['dxcms_pa_lam_notify_patch_issue','dxcms_pa_lam_reboot_first_dependent_instance','dxcms_pa_lam_reboot_other_dependent_instances','dxcms_pa_lam_reboot_other_dependent_instances','dxcms_pa_lam_notify_app_issue','dxcms_pa_lam_SNS_trigger_lambda']


def get_aws_account_info():
    accoundId = ""
    try:
        sts = boto3.client("sts",config=config)
        accoundId = sts.get_caller_identity()["Account"]    
    except:
        print(PrintException())
        accoundId = ""
        sys.exit(1)
    return accoundId


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
        ssm_parameter_value = ssmParameter['Parameter']['Value']
        return ssm_parameter_value
    except:
        print(PrintException())

def create_cloudwatch_rule(region_name):
    try:
        CW_client = boto3.client('events',config=config)
        response = CW_client.put_rule(
            Name='DXCSchedulePatching'+ "_" + region_name,
            ScheduleExpression='cron(0 9 1 * ? *)',
            State='ENABLED',
            Description='Rule to trigger the Schedule Patching State Machine.',
        )
    except:
        print(PrintException())

def create_adhoccloudwatchrule(scheduleexpression):
    try:
        CW_client = boto3.client('events',config=config)
        response = CW_client.put_rule(
            Name = "DXCAdhocSchedulePatching"+ "_" + region,
            EventPattern = json.dumps(scheduleexpression),
            State='ENABLED',
            Description='Rule to trigger the Schedule Patching State Machine.'
        )        
    except:
        print(PrintException())

def add_target_to_cloudwatchrule(rule,input_value,ID,ARN,RoleArn):
    try:
        CW_client = boto3.client('events',config=config)
        lambdaTarget = CW_client.put_targets(
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
        print(PrintException())

def add_invoke_permission(account_id,region):
    try:
        runtime_region = os.environ['AWS_REGION']
        if runtime_region != region:
            client = boto3.client('lambda',config=config)
            for i in range(len(SNS_Topics)):
                try:
                    sns_topic_name = SNS_Topics[i]
                    lambda_fun_name = SNS_Subscriptions[i]
                    topic_arn = 'arn:aws:sns:'+ region +':' + account_id + ':' + sns_topic_name
                    statement_id = sns_topic_name + region
                    print(f"========>>>>>>>>>>>>>>>> {sns_topic_name} =>  {lambda_fun_name}")
                    response = client.add_permission(
                        Action='lambda:InvokeFunction',
                        FunctionName=lambda_fun_name,
                        Principal='sns.amazonaws.com',
                        SourceAccount='338395754338',
                        SourceArn=topic_arn,
                        StatementId=statement_id,
                    )
                except:
                     print(PrintException())
    except:
        print(PrintException())

def create_sns_topic(account_id,region):
    try:
        runtime_region = os.environ['AWS_REGION']  
        #print('This Lambda Function was run in region: ', runtime_region) 
        sns_client = boto3.client('sns',region_name = region,config=config)
        for i in range(len(SNS_Topics)):
            topic_name = SNS_Topics[i]
            endpoint = 'arn:aws:lambda:'+ runtime_region +':' + account_id + ':function:'+ SNS_Subscriptions[i]
            topic_response = sns_client.create_topic(Name=topic_name)
            #print(topic_response['TopicArn'])
            sns_topic_arn = topic_response['TopicArn']
            subscription_arn_response = sns_client.subscribe(
                TopicArn=sns_topic_arn,
                Protocol='lambda',
                Endpoint='arn:aws:lambda:'+ runtime_region +':' + account_id + ':function:'+ SNS_Subscriptions[i],                
                ReturnSubscriptionArn=True
            )
            
            #print("subscription_arn_response : ",subscription_arn_response)    
    except:
        print(PrintException())


def verify_ses_email_ids(email_ids,region):
    try:
        ses_client = boto3.client("ses",region_name=region,config=config)
        for Email_Id in email_ids:
            response = ses_client.verify_email_address(
                EmailAddress=Email_Id
            )
            print("SES Email ID has been created : ", Email_Id)
            print(response)
    except:
        print(PrintException())

def check_bucket_existance(bucket_name):
    s3 = boto3.resource('s3')
    bucket = s3.Bucket(bucket_name)
    print("bucket : ",bucket)
    try:
        s3.meta.client.head_bucket(Bucket=bucket_name)
        print("Bucket Exists!")
        Bucket_existance_status = 'Yes'
        return Bucket_existance_status
    except botocore.exceptions.ClientError as e:
        # If a client error is thrown, then check that it was a 404 error.
        # If it was a 404 error, then the bucket does not exist.
        error_code = int(e.response['Error']['Code'])
        if error_code == 403:
            print("Private Bucket. Forbidden Access!")
            Bucket_existance_status = 'not accessible!'
            return Bucket_existance_status
        elif error_code == 404:
            print("Bucket Does Not Exist!.. Creating one now...")
            Bucket_existance_status = 'No'
            return Bucket_existance_status

def create_bucket(S3_Bucket_Name,Region):
    try:
        s3_client = boto3.client('s3',config=config)
        response = s3_client.create_bucket(
        Bucket=S3_Bucket_Name,
        CreateBucketConfiguration={
            'LocationConstraint': Region
            }
        )
        print(response)
    except:
        print(PrintException())

def create_s3_folder(S3_Bucket_Name,S3_Key):
    try:
        s3_client = boto3.client('s3',config=config)
        response = s3_client.put_object(
        Bucket=S3_Bucket_Name,
        Key=S3_Key
        )
        print(response)
    except:
        print(PrintException())

def copy_healthcheck_config_file(S3_Bucket_Name,S3_Key):
    try:
        s3 = boto3.resource('s3')
        s3_source_file = s3_offering_key_path + "/LambdaFunctions/health_check_config/healthCheckConfig.yml"
        print("s3_source_file : ", s3_source_file)

        copy_source = {
                    'Bucket': S3_offering_bucket,
                    'Key': s3_source_file
                    }

        print("target bucket : ",S3_Bucket_Name)
        target_bucket = s3.Bucket(S3_Bucket_Name)
        target_file = S3_Key + "healthCheckConfig.yml"
        print("S3_Key for config file : ",target_file)
        target_bucket.copy(copy_source, target_file)
        print(f"Health Check Config file has been copied to Automation Report bucket : {S3_Bucket_Name}/{S3_Key}")
    except:
        print(PrintException())

def copy_healthcheck_scripts(S3_Bucket_Name,S3_Key,osname):
    try:
        s3 = boto3.resource('s3')
        offering_bucket = s3.Bucket(S3_offering_bucket)

        lowlevel_script_folder = s3_offering_key_path + "/LambdaFunctions/" + osname + "/"
        print("lowlevel_script_folder : ",lowlevel_script_folder)
        for low_scripts in offering_bucket.objects.filter(Prefix=lowlevel_script_folder):
            lowlevel_script = low_scripts.key
            print("lowlevel_script : ",lowlevel_script)
            if ".ps1" in lowlevel_script or ".sh" in lowlevel_script:
                copy_source = {
                            'Bucket': S3_offering_bucket,
                            'Key': lowlevel_script
                            }
    
                target_file = S3_Key + lowlevel_script.split("/")[len(lowlevel_script.split("/"))-1]
                print("target_file : ", target_file)
                target_bucket = s3.Bucket(S3_Bucket_Name)
                target_bucket.copy(copy_source, target_file)
                print(f"Health Check script file has been copied to Automation Report bucket : {S3_Bucket_Name}/{S3_Key}")
    except:
        print(PrintException())
        

def check_s3_bucket_naming_pattern(S3_Bucket_Name,account_id,region,patching_type):
    if patching_type == 'standard_patching':
            s3_bucket_pattern = f"dxcms.patchingautomation.{account_id}.{region}"
    else:
        s3_bucket_pattern = f"dxcms.adhocpatchingautomation.{account_id}.{region}"

    # s3_bucket_pattern = f"dxcms.adhocpatchingautomation.{account_id}.{region}"
    if s3_bucket_pattern in S3_Bucket_Name:
        print("Naming convention of S3 has been matched.. proceeding further...")
    else:
        raise Exception(f"Naming convention of S3 is incorrect. It should start with {s3_bucket_pattern}")

def lambda_handler(event,context):
    try:
        global local_output_file_path, s3client, client, S3_offering_bucket, s3_offering_key_path
        region = os.environ['AWS_REGION']
        account_id = get_aws_account_info()
        patching_type = read_ssm_parameter(Patching_Type)
        event['patching_type'] = patching_type

        S3_offering_bucket = "awspe-downloads"
        s3_offering_key_path = "patching_automation_health_check"
        if patching_type == 'standard_patching':
            S3_Bucket = "dxcms.patchingautomation." + account_id + "." + region
        else:
            S3_Bucket = "dxcms.adhocpatchingautomation." + account_id + "." + region

        # S3_Bucket = "dxcms.patchingautomation." + account_id + "." + region
        S3_Folder_Name = "patching_reports"
        
        cloudops_email_id = read_ssm_parameter(CloudOps_Email_IDs)
        cloudops_team_email_id = read_ssm_parameter(CloudOps_Teams_Channel)
        sender_email_id = read_ssm_parameter(Sender_Email_ID)
        cloudops_email_id = cloudops_email_id.split(";")
        cloudops_team_email_id = cloudops_team_email_id.split(";")
        sender_email_id = sender_email_id.split(";")
        if cloudops_team_email_id == '':
            email_ids = list(set(cloudops_email_id + sender_email_id))
        else:
            email_ids = list(set(cloudops_email_id + cloudops_team_email_id + sender_email_id))

        check_s3_bucket_naming_pattern(S3_Bucket,account_id,region,patching_type)
        s3_bucket_existance_status = check_bucket_existance(S3_Bucket)
        if s3_bucket_existance_status == "No":
            create_bucket(S3_Bucket,region)

        s3_key_config_file = S3_Folder_Name + "/HealthCheckConfigAndScripts/ConfigFile/"
        create_s3_folder(S3_Bucket,s3_key_config_file)
        #copy_healthcheck_config_file(S3_Bucket,s3_key_config_file)
        s3_key_low_level_windows = S3_Folder_Name + "/HealthCheckConfigAndScripts/LowLevelScripts/Windows/"
        create_s3_folder(S3_Bucket,s3_key_low_level_windows)
        #copy_healthcheck_scripts(S3_Bucket,s3_key_low_level_windows,"Windows")
        s3_key_low_level_linux = S3_Folder_Name + "/HealthCheckConfigAndScripts/LowLevelScripts/Linux/"
        create_s3_folder(S3_Bucket,s3_key_low_level_linux)
        #copy_healthcheck_scripts(S3_Bucket,s3_key_low_level_linux,"Linux")


        verify_ses_email_ids(email_ids,region)


        if patching_type == 'standard_patching':
            create_cloudwatch_rule(region)
            input_value = {"TagName": "Downtime Window","region":region,"S3_Bucket" : S3_Bucket,"S3_Folder_Name": S3_Folder_Name }
            rule_name = 'DXCSchedulePatching' + "_" + region
            
        else:
            rule_name = 'DXCAdhocSchedulePatching' + "_" + region
            input_value = {"TagName": "Adhoc Downtime Window","region":region,"S3_Bucket" : S3_Bucket,"S3_Folder_Name": S3_Folder_Name }
            state_machine_arn = 'arn:aws:states:'+region+':'+account_id+':stateMachine:dxcms_pa_sfn_schedule_patching'
            rule_event_pattern = {
                "source": ["aws.lambda"],
                "detail-type": ["Lambda Function Invocation Result - Success"],
                "detail": {
                    "requestParameters": {
                        "functionName": ['dxcms-pa-lam-enable-patching-automation']
                    }
                }
            }
            create_adhoccloudwatchrule(rule_event_pattern)
        add_target_to_cloudwatchrule(rule_name,input_value,Sfnname,StepFunArn,StepFunRoleArn)

        return event
    except:
        print(PrintException())
        sys.exit(1)


if __name__ == "__main__":
    #event1 = {"TagName": "Downtime Window"}
    # Provide SES Offering BUCKET NAME which is used for Offering Deployment
    # Provide SES Offering version S3 LambdaFunctions Folder path
    event1 = {

            }
    lambda_handler(event1, "")

        
        
