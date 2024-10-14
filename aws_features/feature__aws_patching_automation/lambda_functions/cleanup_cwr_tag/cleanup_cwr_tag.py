''' cleanup_cwr_tag lambda function will delete rule and tag value in case of patching windows missed or cancelled
sample event
{
  "S3_Bucket": "dxcms.patchingautomation.567529657087.ap-southeast-2",
  "S3_directory_name": "JUN_2023/ap-southeast-2",
  "S3_Folder_Name": "patching_reports",
  "region": "ap-southeast-2",
  "Tag_Value": "PKT-JUN_18_2023_4_0_4HRS",
  "Trigger_Rule_Name": "Patching_Window_Check_PKT-JUN_18_2023_4_0_4HRS"
}

where "Trigger_Rule_Name" is needed only when patching window is missed.

'''

import boto3
import sys
import csv
import json
import os
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))
lambda_client = boto3.client('lambda',config=config)
LF_ID_pw_status_check = os.environ['PatchingWindow_status_check'] #'dxcms-pa-lam-check-pw-status'
LF_ID_Snow_status_check = os.environ['Service_now_status_check']

'''Printexception function is created for handling an error
this function returns the line number where error that occured '''

def PrintException():
    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    captureErr = "Line No. : " + str(lineno)  + " | ERROR: " + str(exc_obj)
    return captureErr

'''Account_check function is getting use for  fetching account number and account name '''
def account_check():
    print("account_check function called")
    try:
        account_id = boto3.client('sts', config=config).get_caller_identity().get('Account')
        account_name = boto3.client('iam', config=config).list_account_aliases()['AccountAliases'][0]
        return account_name,account_id
    except:
        exception=PrintException()
        print(exception)
        print("==============================================")
        # print("Something went wrong in:"+account_id)
        # print("Something went wrong in:"+account_name)
        
'''Create Report function is getting use for create csv files '''
def create_report(filename, csv_list,flag):
    print("Create csv function called")
    headers = ['Account Number', 'Account Name', 'Resource Type','Resource','Tag Value']
    try:
        with open(filename, 'a', newline='') as csvfile:
            csvwriter = csv.writer(csvfile)
            if flag:
                csvwriter.writerow(headers)
            csvwriter.writerows(csv_list)

    except:
        exception = PrintException()
        print(exception)


'''Delete rule function is use to delete the amazon event bridge rule with the rule prefix , it is first removing the 
target which is available in rule_prefixes then it is deleting the rule and after that it is appending the rules name
in csv file'''
def delete_rule(Resource_name,local_path,account_id,account_name):
    rule_prefixes = ['Install_Patch_' + TagValues +'_'+region, 'PatchScan_'+ TagValues +'_'+region, 'Peform_PreTask_'+ TagValues +'_'+region, 'SNOW_CR_Status_Check_'+ TagValues, 'Patching_Window_Check_' + TagValues]
    flag=True
    deleted_rules=[]
    csv_list=[]
    try:
        eventbridge = boto3.client('events',config=config)
        for prefix in rule_prefixes:
            # rule_prefix_name = prefix + TagValues + '_' + region

            response = eventbridge.list_rules(NamePrefix=prefix)

            for rule in response['Rules']:
                if rule['Name'].startswith(prefix):
                    rule_name=rule['Name']
                    response = eventbridge.list_targets_by_rule(Rule=rule_name)
                                
                    for target in response['Targets']:
                        target_id = target['Id']
                        eventbridge.remove_targets(Rule=rule_name, Ids=[target_id])
                        print(f"Removed target {target_id} from rule: {rule_name}")                 
                    eventbridge.delete_rule(Name=rule_name)
                    deleted_rules.append(rule_name)
                    print(f"Deleted EventBridge rule: {rule_name}")
                    break
            else:
                print(f"No rule found with prefix: {prefix}")
        for d in deleted_rules:
            print(d)
            csv_list.append([account_id,account_name,Resource_name,d,TagValues])
        create_report(local_path+filename,csv_list,flag)
        
        #Remove trigger permission from lambda
        statement_dict = {}
        statement_dict[LF_ID_pw_status_check] = 'PatchingWindowCheck_'+TagValues
        statement_dict[LF_ID_Snow_status_check] = 'Patching_'+TagValues
        try:
            for skey,svalue in statement_dict.items():
                print(skey,svalue)
                response = lambda_client.remove_permission(
                            FunctionName=skey,
                            StatementId=svalue)
                print("Lambda Permission removed for ",svalue)
        except:
            print("No Permission found: ", svalue)
        # return deleted_rules
    except:
        exception = PrintException()
        print(exception)
           

    
'''Delete tag function is used to delete the patching tag, it will first search with PatchInstallOn tag and on that instance 
id it will search for PatchInstallTemp tag and if it is available then it will take a value of PatchInstallTemp and it will delete it
then value of PatchInstallTemp will be add on the place of PatchInstallOn
if PatchInstallTemp is not available then it will delete PatchInstallOn by taking tag value from event also it will 
append instance_id and tag value which it is deleted in csv file'''

def delete_tag(Resource_name,local_path,account_id,account_name):
    flag=False
    csv_list=[]

    try:
        tag_key = 'PatchInstallOn'
        tag_key_temp='PatchInstallTemp'
        tag_value = TagValues
        instance_ids = []
        temp_instance_ids=[]
        
        ec2_client = boto3.client('ec2',config=config)
        response = ec2_client.describe_instances(
            Filters=[
                {
                    'Name': 'tag:' + tag_key,
                    'Values': [tag_value +'*']
                }
            ]
        )
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                instance_id = instance['InstanceId']
                instance_ids.append(instance_id)
                
                # temp_tag=False
                temp_tag_value=None
                for tag in instance['Tags']:
                    if tag['Key'] == tag_key_temp:
                        temp_tag_value = tag['Value']
                        temp_instance_ids.append(instance_id)
                        break
                if temp_tag_value:
                    ec2_client.create_tags(
                        Resources=[instance_id],
                        Tags=[
                            {
                                'Key': 'PatchInstallOn',
                                'Value': temp_tag_value
                            }
                        ]
                    )
                    print(f"Updated 'PatchInstallOn' tag value for instance '{instance_id}' with '{temp_tag_value}'")
                    
                    ec2_client.delete_tags(
                        Resources=[instance_id],
                        Tags=[
                            {
                                'Key': 'PatchInstallTemp',
                                'Value': temp_tag_value
                            }
                        ]
                    )
                    print(f"Deleted 'PatchInstallTemp' tag for instance '{instance_id}'")
                else:
                    for tag in instance['Tags']:
                        if tag['Key'] == tag_key and tag['Value'].startswith(tag_value):
                            # instance_ids.append(instance_id)
                            print(f"Deleting PatchInstallOn tag with tag value:{tag_value}")
                        ec2_client.delete_tags(
                            Resources=[instance_id],
                            Tags=[
                                {
                                    'Key': tag_key,
                                    'Value': tag['Value']
                                }
                            ]
                        )
                    # instance_ids.append(instance_id + ',' + tag_value)
        
        print("Instance id where PatchInstallTemp was found:",temp_instance_ids) 
            
        if instance_ids==None or instance_ids=="" or instance_ids==[]:
            print(f"No Instance Id found with PatchInstallOn tag value : {TagValues} .")
        else:
            print(f"Instance Id Found with PatchInstallOn tag value:{TagValues} .")
            for i in instance_ids:
                print(i)
                csv_list.append([account_id,account_name,Resource_name,i,tag_value])
        create_report(local_path+filename,csv_list,flag)
        # return instance_ids
    except:
        exception = PrintException()
        print(exception)
        
'''This (upload file)Function is uploading the given csv reports to
bucket at particular key location which is provided''' 

def upload_file(bucket_name,bucket_key, local_uri):
    print("file is uploading and saving to bucket:",end=' ')
    s3 = boto3.resource('s3', config=config)
    try:
        #print(file_uri)
        s3.meta.client.upload_file(local_uri, bucket_name, bucket_key)
        print( bucket_key)
        return True
    except:
        exception = PrintException()
        print(exception)

'''This (read_config_file) Function reads data from Patching_config.json 
and gets the patchJob_id for the particular TagValue''' 
def read_config_file(S3_Bucket, S3_directory_name,TagValues):
    try:
        s3client = boto3.client('s3',config=config)
        directory_name = S3_Folder_Name + "/" + "PATCHING" + "/" + S3_directory_name + "/" + "Patching_config.json"
        response = s3client.get_object(Bucket=S3_Bucket, Key=directory_name)
        content = response['Body']
        config_dict = json.loads(content.read())
        #print(type(config_dict), config_dict)
        patchJob_id = config_dict['patchJobIds'][TagValues]
        print("Tag:", TagValues, "PatchJobId:", patchJob_id)
    except:
        print(PrintException())

    return patchJob_id


def lambda_handler(event,context):
    # received_event = json.loads(event)
    global region
    global TagValues
    global bucket_name
    global filename
    global S3_directory_name
    global S3_Folder_Name
    S3_directory_name = event['S3_directory_name']
    S3_Folder_Name = event["S3_Folder_Name"]
    
    region = event['region']
    TagValues = event['Tag_Value']   
    account_name,account_id=account_check()
    filename ="Deleted_tag_rule" + "_" + TagValues + ".csv"
    local_path = "/tmp/"  
    bucket_name = event["S3_Bucket"]
    patchJob_id = read_config_file(bucket_name,S3_directory_name,TagValues)
    
    if "Trigger_Rule_Name" in event.keys():
        bucket_key = S3_Folder_Name +'/PATCHING/'+ S3_directory_name +'/Patching-Windows-missed/'
        event["attribute_value"] = "missed"
    else:
        bucket_key = S3_Folder_Name +'/PATCHING/'+ S3_directory_name +'/Patching-Windows-Cancelled/'
        event["attribute_value"] = "cancelled"
    
    delete_rule("Rule",local_path,account_id,account_name)
    delete_tag("Tag",local_path,account_id,account_name)
    upload_file(bucket_name,bucket_key+filename,local_path+filename)

    # List all files in the '/tmp' directory
    files = os.listdir(local_path)
    # Remove each file in the '/tmp' directory
    for file_name in files:
        file_path = os.path.join(local_path, file_name)
        os.remove(file_path)
    
    #event["statusCode"] = 200
    #event["body"] = 'All temporary files deleted.'
    event["patchJob_id"] = patchJob_id
    event["attribute_name"] = "patch_job_status"
    
    return event

if __name__ == "__main__":

    event1 = {
  "S3_Bucket": "dxcms.patchingautomation.567529657087.eu-west-3",
  "S3_directory_name": "AUG_2023/eu-west-3",
  "S3_Folder_Name": "patching_reports",
  "region": "eu-west-3",
  "Tag_Value": "PROD-AUG_17_2023_6_0_3HRS"
    }

    lambda_handler(event1, "")
