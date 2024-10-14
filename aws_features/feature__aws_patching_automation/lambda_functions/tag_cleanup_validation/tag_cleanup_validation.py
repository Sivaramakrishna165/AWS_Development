'''This lambda function is use to validate PatchinstallOn tag is delete or not
  event1 = {
  "PatchInstallOn": "PKT-APR_28_2023_13_5_4HRS",
  "S3_Bucket": "dxcms.patchingautomation.567529657087.ap-southeast-2",
  "S3_directory_name": "APR_2023/ap-southeast-2/patchJobId_52f1204c-e348-11ed-8638-03b6b0063f57",
  "S3_Folder_Name": "patching_reports",
  "region": "ap-southeast-2"
    }
'''
import boto3
import sys
import csv
from operator import itemgetter
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))

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

def create_report(filename, csv_list):
    print("Create csv function called")
    headers = ['Account Name','Account Id','Instance id','Status']
    print(filename)
    allowed_filepath = "/tmp/Tag Validation_" + TagValues + ".csv"
    try:
        if filename == allowed_filepath:
            with open(filename, 'w', newline='') as csvfile:
                csvwriter = csv.writer(csvfile)
                csvwriter.writerow(headers)
                csvwriter.writerows(csv_list)

    except:
        exception = PrintException()
        print(exception)


'''Fetch instance function is getting use for list down the instance id from server list from s3 bucket '''

def fetch_instance_pass():
    # ec2 = boto3.resource('ec2',region_name=region)
    client = boto3.client('ec2',region_name=region,config=config)
    s3 = boto3.resource('s3',config=config)
    try:
        instance_Ids = []
        # instanceTags = ("*" + TagValues + "*")
        obj = s3.Object(bucket_name, file_key)
        data = obj.get()['Body'].read().decode('utf-8').splitlines()
        reader = csv.reader(data)
        next(reader)
        for row in reader:
            print(row[0])
            instance_Ids.append(row[0])
        print(instance_Ids)
        
        return instance_Ids
    except:
        exception=PrintException()
        print(exception)


'''Fetch instance_id function getting use for list down the server list which have PatachInstallOn tag'''

def fetch_instance_ids(TagValues,patch_type):
    # ec2 = boto3.resource('ec2',region_name=region)
    client = boto3.client('ec2',region_name=region,config=config)
    try:
        instanceIds = []
        instanceTags = ("*" + TagValues + "*")
        response = client.describe_instances(
            Filters=[
                {
                    'Name': 'tag:'+patch_type,
                    'Values': [
                         instanceTags,
                    ]
                },
            ]
            )    
        for r in response['Reservations']:
            for i in r['Instances']:
                instanceIds.append(i['InstanceId'])
        return instanceIds
    except:
        print(PrintException())

'''This cleanup_validation Function will check Instance id in serverlist.csv from s3 bucket in Fetch_instance_pass 
function and then it will search with PatchInstallOn inside serverlist.csv instance id if PatchInstallOn tag is
present then it will save Status Fail with instance id in csv ,if it is not available then it will Store status as
Pass in CSV '''
def cleanup_validation(patch_type):
    print("Cleanup Validation Function called")
    try:
        account_name,account_id=account_check()
        csv_list=[]
        InstanceIds=fetch_instance_ids(TagValues,patch_type)
        dlist=fetch_instance_pass()
        for instance_id in dlist:
            if instance_id in InstanceIds:
            # print(f"FAIL: {instance_id}")
                print(f"Instance Id found :{instance_id}  with matching tag value : {TagValues} . Hence it's not a clean")
                status="Fail"
                csv_list.append([account_name,account_id,instance_id,status])
            else:
                status="Pass"
                # print(f"PASS: {instance_id}")
                csv_list.append([account_name,account_id,instance_id,status])
        return csv_list
    except:
        print(PrintException())

'''This (upload file)Function is uploading the given csv reports of
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


def lambda_handler(event,context):
    global region
    global TagValues
    global bucket_name
    global file_key
    region = event['region']
    TagValues = event['PatchInstallOn']  
    Patching_Type= event['Patching_Type']
    if Patching_Type == 'Adhoc':
        patch_type = 'AdhocPatchInstallOn'
    else:
        patch_type = 'PatchInstallOn' 
    # local_path= r'C:\Users\pkumar745\OneDrive - DXC Production\Documents\python program'
    file_key=event["S3_Folder_Name"]+'/PATCHING/'+ event["S3_directory_name"] +'/ServersList/' + "PatchServerList_" + TagValues + ".csv"
    filename ="Tag Validation" + "_" + TagValues + ".csv"
    local_path = "/tmp/"  
    bucket_name = event["S3_Bucket"]
    bucket_key= event["S3_Folder_Name"]+'/PATCHING/'+ event["S3_directory_name"] +'/Cleanup Validation/'
    csv_list=cleanup_validation(patch_type)
    create_report(local_path+filename,csv_list)
    upload_file(bucket_name,bucket_key+filename,local_path+filename)
    return event
    


if __name__ == "__main__":
    #PatchInstallOnTagValues = ['APR_4_2021_14_30_4HRS', 'APR_11_2021_14_30_4HRS', 'APR_4_2021_03_30_4HRS', 'APR_18_2021_14_30_4HRS']
    event1 = {
  "PatchInstallOn": "PKT-APR_28_2023_13_5_4HRS",
  "S3_Bucket": "dxcms.patchingautomation.567529657087.ap-southeast-2",
  "S3_directory_name": "APR_2023/ap-southeast-2/patchJobId_52f1204c-e348-11ed-8638-03b6b0063f57",
  "S3_Folder_Name": "patching_reports",
  "region": "ap-southeast-2"
    }
    #event1 = {"TagValues": PatchInstallOnTagValues }

    lambda_handler(event1, "")
