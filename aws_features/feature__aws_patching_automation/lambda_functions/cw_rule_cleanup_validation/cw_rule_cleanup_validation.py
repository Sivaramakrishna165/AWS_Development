'''This lambda funtion will check amazon eventbridge rule is deleted in post phase or not
  event1 = {
  "PatchInstallOn": "PatchTest-MAR_30_2023_5_30_4HRS",
  "S3_Bucket": "dxcms.patchingautomation.567529657087.ap-southeast-1",
  "S3_directory_name": "MAR_2023/ap-southeast-1/patchJobId_8f37c24e-c3e3-11ed-aa78-27f543885363",
  "S3_Folder_Name": "patching_reports",
  "region": "ap-southeast-1"
    }'''
import boto3
import sys
import csv
from operator import itemgetter
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))
client = boto3.client('events',config=config)
#ssm_parameter = "/DXC/PatchingAutomation/Enable_SNOW_Integration"

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
        
'''This function is use to create_csvfile reports in csv file'''
def create_csvfile(filename, csv_list):
    print("Create csvfiles function called")
    headers = ['Account Name', 'Account ID', 'Rule count','Status','Rules Available']
    allowed_path = "/tmp/Amazon Event Bridge Rule" + "_" + TagValues + ".csv"
    try:
        if filename == allowed_path:
            with open(filename, 'w', newline='') as csvfile:
                csvwriter = csv.writer(csvfile)
                csvwriter.writerow(headers)
                csvwriter.writerows(csv_list)
    except:
        exception = PrintException()
        print(exception)


# def read_ssm_parameter(ssm_parameter):
#     try:
#         ssm_client = boto3.client('ssm',config=config)
#         ssmParameter = ssm_client.get_parameter(Name=ssm_parameter)
#         snow_status = ssmParameter['Parameter']['Value']
#         return snow_status
#     except:
#         exception = PrintException()
#         print(exception)


'''This function will check Amazon event bridge rule is available or not and it will append in list'''

def get_matching_rules(TagValues):
    print("get matching rules function called")
    try:
        matching_rules = []
        # snow_enable_status=read_ssm_parameter(ssm_parameter)
        response = client.list_rules()
        for rule in response['Rules']:
            if rule['Name'].startswith('Install_Patch_' + TagValues):
                matching_rules.append(rule['Name'])
            if rule['Name'].startswith('PatchScan_' + TagValues):
                matching_rules.append(rule['Name'])
            if rule['Name'].startswith('Peform_PreTask_' + TagValues):
                matching_rules.append(rule['Name'])
            # if snow_enable_status == "ON":
            if rule['Name'].startswith('SNOW_CR_Status_Check_' + TagValues):
                print("Snow is enable")
                matching_rules.append(rule['Name'])
            if rule['Name'].startswith('Patching_Window_Check_' + TagValues):
                print("Snow is Disable")
                matching_rules.append(rule['Name'])
            
        return matching_rules
    except:
        exception = PrintException()
        print(exception)

'''This function is use to store status and rule count to the csv '''

def validate_rules(rule_list):
    print("Validate_rules Function called")
    try:
        account_name,account_id=account_check()
        csv_list=[]
        count_rule=len(rule_list)
        if rule_list== [] or rule_list== "" or rule_list== None:
            print('No Amazon Event bridge rule found related to the Patching cleanup validation')
            csv_list.append([account_name,account_id,count_rule,"PASS"," "])
        else:
            
            print("Amazon Event bridge rule count related to the patching is :",count_rule)
            csv_list.append([account_name,account_id,count_rule,"FAIL",rule_list])
        return csv_list
    except:
        exception = PrintException()
        print(exception)

'''This function use to upload reports to the s3 bucket'''

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


def lambda_handler(event,context):
    global region
    region = event['region']
    global TagValues
    TagValues = event['PatchInstallOn'] 
    # local_path= r'C:\Users\pkumar745\OneDrive - DXC Production\Documents\python program'
    filename ="Amazon Event Bridge Rule" + "_" + TagValues + ".csv"
    local_path = "/tmp/" 
    bucket_name = event["S3_Bucket"]
    bucket_key= event["S3_Folder_Name"]+'/PATCHING/'+ event["S3_directory_name"] +'/Cleanup Validation/'
    matching_rule=get_matching_rules(TagValues)
    csv_list=validate_rules(matching_rule)
    create_csvfile(local_path+filename,csv_list)
    upload_file(bucket_name,bucket_key+filename,local_path+filename)
    return event
    

if __name__ == "__main__":
    #PatchInstallOnTagValues = ['APR_4_2021_14_30_4HRS', 'APR_11_2021_14_30_4HRS', 'APR_4_2021_03_30_4HRS', 'APR_18_2021_14_30_4HRS']
    event1 = {
  "PatchInstallOn": "PatchTest-MAR_30_2023_5_30_4HRS",
  "S3_Bucket": "dxcms.patchingautomation.567529657087.ap-southeast-1",
  "S3_directory_name": "MAR_2023/ap-southeast-1/patchJobId_8f37c24e-c3e3-11ed-aa78-27f543885363",
  "S3_Folder_Name": "patching_reports",
  "region": "ap-southeast-1"
    }
    #event1 = {"TagValues": PatchInstallOnTagValues }

    lambda_handler(event1, "")
