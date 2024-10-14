'''
This script creates the Change Request in SNOW for every patching schedule and will notify to the CloudOps team
'''

import boto3
import requests 
from requests.auth import HTTPBasicAuth 
import json
import sys
import os
import datetime
import base64
from botocore.exceptions import ClientError
from requests.models import encode_multipart_formdata
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))
region = os.environ['AWS_REGION']
secret_manager_name = os.environ['Secret_Name']
Reference_CR_No = os.environ['Reference_CR_No']


body = {
    "category": "Applications Software",
    "type": "Normal",
    "short_description": "[DXC PATCHING AUTOMATION] Applying Latest Patches to the AWS Instances....",
    "company": "0971e120db3122006052fd9eaf9619c9",
    "impact": 3,
    "urgency": 2,
    "priority": 3,
    "risk": 4,
    "justification": "[INTERNAL] DANWAY_Patching_25_MAY _2022_ Prod Servers",
    "start_date": "2022-05-21 19:09:23",
    "end_date": "2022-05-25 20:51:23",
    "assignment_group": "",
    "cmdb_ci":"",
    "change_plan":"",
    "implementation_plan":"",
    "backout_plan":"",
    "test_plan":"",
    "description":"[DXC PATCHING AUTOMATION] Applying Latest Patches to the AWS Instances...."
}


def PrintException():
    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    captureErr = "Line No. : " + str(lineno)  + " | ERROR: " + str(exc_obj)
    return captureErr

def read_ssm_parameter(parameter_name):
    ssm_para_client = boto3.client('ssm',config=config)
    response = ssm_para_client.get_parameter(
        Name=parameter_name,
    )
    ssm_parameter = response['Parameter']
    ssm_parameter_value = ssm_parameter['Value']
    return ssm_parameter_value

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
        
        
def read_data_from_config_file(S3_Bucket,S3_directory_name,TagValues):
    Keyname1 = 'executepatchscan'
    Keyname2 = 'patchJobIds'
    s3client = boto3.client('s3',config=config)
    directory_name = S3_Folder_Name + "/" + "PATCHING" + "/" + S3_directory_name + "/" + "Patching_config.json"
    response = s3client.get_object(Bucket=S3_Bucket, Key=directory_name)
    content = response['Body']
    jsonObject = json.loads(content.read())
    execute_patch_scan_json_object = filter_json(TagValues,jsonObject[Keyname1])
    patchJobIds_json_object = filter_json(TagValues,jsonObject[Keyname2])
    # Finding the End date of the patching.
    patchJob_ids = []
    Tagvalue_with_grp_name = []
    for tag,patch_id in patchJobIds_json_object.items():
        Tagvalue_with_grp_name.append(tag)
        patchJob_ids.append(patch_id)
    TagValues = []
    patch_start_date = []
    patch_end_date = []
    for key,value in execute_patch_scan_json_object.items():
        tagvalue = key.split('-')[1]
        TagValues.append(tagvalue)
        downtime = tagvalue.split("_")[5]
        minutes = tagvalue.split("_")[4]
        hours = tagvalue.split("_")[3]
        date = tagvalue.split("_")[1]
        month = tagvalue.split("_")[0]
        year = tagvalue.split("_")[2]
        downtime = int(downtime.split('HRS')[0])
        print("downtime : ",downtime)
        print("minutes : ",minutes)
        print("hours : ",hours)
        print("date : ",date)
        print("month : ",month)
        print("year : ",year)
        patchInstallDate_str = str(date) + "-" +  str(month) + "-" + str(year) + "-" + str(hours) + "-" + str(minutes)
        patchInstallDate = datetime.datetime.strptime(patchInstallDate_str, '%d-%b-%Y-%H-%M')
        print(patchInstallDate)
        #print("1. PATCH INSTALL DATE (patchInstallDate): ", patchInstallDate)
        patch_start_date.append(str(patchInstallDate))
        patchScanDate = patchInstallDate + datetime.timedelta(hours= +int(downtime))
        print(patchScanDate)
        #print("2. PATCH End DATE (patchInstallDate): ", patchScanDate)
        patch_end_date.append(str(patchScanDate))   
    return TagValues,patch_start_date,patch_end_date,Tagvalue_with_grp_name,patchJob_ids


def fetch_reference_cr(secret):
    try:
        cr_number = read_ssm_parameter(Reference_CR_No)
        # set the credential
        credential = json.loads(secret)
        username = credential['snowuser']
        password = credential['snowpassword']
        Snow_url = credential['snowhost']
        # url = "https://csctest.service-now.com/api/sn_chg_rest/change?sysparm_query=number=CHG0121830"
        url = Snow_url + "/api/sn_chg_rest/change?sysparm_query=number=" + cr_number
        # Set the proper headers
        headers = {"Accept":"application/json"} 
        # Make the HTTP request
        response = requests.get(str(url), auth=(username, password), headers=headers)
        # Check for HTTP codes other than 200
        if response.status_code != 200: 
            print('Status:', response.status_code, 'Headers:', response.headers, 'Error Response:', response.content)
            exit()
        print(response.content.decode('utf-8'))
        cr_details = response.content.decode('utf-8')
        cr_details_json = json.loads(cr_details)
        # print("cr_details_json : ",cr_details_json)
        print("=================================================================================")
        # Company details
        company_display_value = cr_details_json["result"][0]['company']['display_value']
        print("company_display_value : ",company_display_value)
        company_value = cr_details_json["result"][0]['company']['value']
        print("company_value : ",company_value)
        print("=================================================================================")
        # Assignment Group Details
        assignment_group_display_value = cr_details_json["result"][0]['assignment_group']['display_value']
        print("assignment_group_display_value : ",assignment_group_display_value)
        assignment_group_value = cr_details_json["result"][0]['assignment_group']['value']
        print("assignment_group_value : ",assignment_group_value)
        print("=================================================================================")
        # Sys id details
        sys_id_display_value = cr_details_json["result"][0]['sys_id']['display_value']
        print("sys_id_display_value : ",sys_id_display_value)
        sys_id_value = cr_details_json["result"][0]['sys_id']['value']
        print("sys_id_value : ",sys_id_value)
        print("=================================================================================")
        category_value = cr_details_json["result"][0]['category']['value']
        print("category : ",category_value)
        print("=================================================================================")
        type = cr_details_json["result"][0]['type']['value']
        print("type : ",cr_details_json["result"][0]['type']['value'])
        print("=================================================================================")
        short_description = cr_details_json["result"][0]['short_description']['value']
        print("short_description : ",cr_details_json["result"][0]['short_description']['value'])
        print("=================================================================================")
        CI_value = cr_details_json["result"][0]['cmdb_ci']['value']
        print("CI_value : ",cr_details_json["result"][0]['cmdb_ci']['value'])
        print("=================================================================================")
        impact = cr_details_json["result"][0]['impact']['value']
        print("impact : ",cr_details_json["result"][0]['impact']['value'])
        print("=================================================================================")
        priority = cr_details_json["result"][0]['priority']['value']
        print("priority : ",cr_details_json["result"][0]['priority']['value'])
        print("=================================================================================")
        change_plan = cr_details_json["result"][0]['change_plan']['value']
        print("change_plan : ",cr_details_json["result"][0]['change_plan']['value'])
        print("=================================================================================")
        implementation_plan = cr_details_json["result"][0]['implementation_plan']['value']
        print("implementation_plan : ",cr_details_json["result"][0]['implementation_plan']['value'])
        print("=================================================================================")
        backout_plan = cr_details_json["result"][0]['backout_plan']['value']
        print("backout_plan : ",cr_details_json["result"][0]['backout_plan']['value'])
        print("=================================================================================")
        test_plan = cr_details_json["result"][0]['test_plan']['value']
        print("test_plan : ",cr_details_json["result"][0]['test_plan']['value'])
        print("=================================================================================")
        description = cr_details_json["result"][0]['description']['value']
        print("description : ",cr_details_json["result"][0]['description']['value'])
        print("=================================================================================")
        urgency = cr_details_json["result"][0]['urgency']['value']
        print("urgency : ",cr_details_json["result"][0]['urgency']['value'])
        print("=================================================================================")
        risk = cr_details_json["result"][0]['risk']['value']
        print("risk : ",cr_details_json["result"][0]['risk']['value'])
        return company_value,assignment_group_value,sys_id_value,category_value,CI_value,impact,priority,change_plan,implementation_plan,backout_plan,test_plan,description,urgency,type,short_description,risk
    except:
        print(PrintException())


def creat_change_request(body,secret):   
    try:  
        # set the credential
        credential = json.loads(secret)
        # unzip the dictionary object....
        username = credential['snowuser']
        password = credential['snowpassword']
        Snow_url = credential['snowhost']
        print("Username : ",username)
        print("password : ",password)
        url = Snow_url + "/api/sn_chg_rest/change"
        print("SNOW_URL : ",url) 
        headers = {
                    'Accept': 'application/json'
                }
        payload = json.dumps(body)
        print("Body : ",payload)
        # user = 'comsappuser.gtc2'
        # pwd = 'gtc2'
        response = requests.request("POST", str(url), headers=headers, data = payload, auth = (username, password), verify=True)
        print("response : ",response)
        if ((response.status_code == 200) or (response.status_code == 201)):
            print("response : ",response)
            cr = response.text  
            print(cr)          
        else:
            cr = "CR CANNOT BE placed"
            error = response.text
            return error
        return cr
    except:
        error = sys.exc_info()
        return error

def get_secret():
    try:
        secret_name = secret_manager_name
        print("Scret name : ", secret_name)
        
        # Create a Secrets Manager client
        session = boto3.session.Session()
        client = session.client(service_name='secretsmanager')
        # In this sample we only handle the specific exceptions for the 'GetSecretValue' API.
        # See https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
        # We rethrow the exception by default.
    
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
        # Decrypts secret using the associated KMS CMK.
        # Depending on whether the secret is a string or binary, one of these fields will be populated.
        if 'SecretString' in get_secret_value_response:
            secret = get_secret_value_response['SecretString']
        else:
            secret = base64.b64decode(get_secret_value_response['SecretBinary'])
        return secret
    except:
        print(PrintException())
    


def convert_time(patch_start_date,patch_end_date):
    formatted_start_time = []
    formatted_end_time = []
    for tagvalue in patch_start_date:
        #2021-07-21 06:00:00
        first_spit = tagvalue.split(" ")
        seconds = first_spit[1].split(":")[2]
        minutes = first_spit[1].split(":")[1]
        hours = first_spit[1].split(":")[0]
        date = first_spit[0].split("-")[2]
        month = first_spit[0].split("-")[1]
        year = first_spit[0].split("-")[0]
        #print(year,month,date,hours,minutes,seconds)
        d = datetime.datetime(int(year), int(month), int(date), int(hours), int(minutes), int(seconds))
        #, tzinfo=pytz.utc)
        utc_time = d.strftime('%Y-%m-%d %H:%M:%S')
        formatted_start_time.append(str(utc_time))
    for tagvalue in patch_end_date:
        first_spit = tagvalue.split(" ")
        seconds = first_spit[1].split(":")[2]
        minutes = first_spit[1].split(":")[1]
        hours = first_spit[1].split(":")[0]
        date = first_spit[0].split("-")[2]
        month = first_spit[0].split("-")[1]
        year = first_spit[0].split("-")[0]
        #print(year,month,date,hours,minutes,seconds)
        d = datetime.datetime(int(year), int(month), int(date), int(hours), int(minutes), int(seconds))
        #, tzinfo=pytz.utc)
        utc_time = d.strftime('%Y-%m-%d %H:%M:%S')
        formatted_end_time.append(str(utc_time))
    return formatted_start_time,formatted_end_time


def update_config_file(S3_Bucket,S3_directory_name,change_request):
    try:
        s3 = boto3.resource('s3')
        itemname = S3_Folder_Name + "/" + "PATCHING/" + S3_directory_name + "/Patching_config.json"
        obj = s3.Object(S3_Bucket, itemname)
        body = obj.get()['Body'].read().decode("utf-8")
        Patching_config = json.loads(body)
        Patching_config['Change_Request'] = change_request
        print(Patching_config)
        localFolder = '/tmp/Patching_config.json'
        with open(localFolder, 'w') as outfile:
            json.dump(Patching_config, outfile)
        bucket = s3.Bucket(S3_Bucket)
        S3Key_for_congif_file = S3_Folder_Name + "/" +"PATCHING/" + S3_directory_name + "/Patching_config.json"
        bucket.upload_file(localFolder, S3Key_for_congif_file)
        return Patching_config
    except:
        print(PrintException())

def call_update_dynamodb_lambda_function(patchJob_ids,attribute_name,attribute_value):
    lambda_client = boto3.client('lambda',config=config)
    for i in range(len(patchJob_ids)):
        dynamo_event = {'patchJob_id': patchJob_ids[i],'attribute_name':attribute_name,'attribute_value':attribute_value[i]}
        response = lambda_client.invoke(
            FunctionName='dxcms-pa-lam-update-dynamodb',
            Payload=json.dumps(dynamo_event)
        )

def encode_csv_to_base(S3_Bucket,S3_directory_name,patch_job_id,Tagvalue):
    s3client = boto3.client('s3',config=config)
    directory_name = S3_Folder_Name + "/" + "PATCHING"+"/"+ S3_directory_name + "/" + patch_job_id+"/ServersList/" + "PatchServerList_" + Tagvalue + ".csv"
    response = s3client.get_object(Bucket=S3_Bucket, Key=directory_name)
    content = response['Body']
    encoded = base64.b64encode(content.read())
    file_data = encoded.decode('utf-8')
    return file_data


def attch_file_to_CR(attachment_file_name,file_content,secret,sys_id):   
    try:    
        credential = json.loads(secret)
        username = credential['snowuser']
        password = credential['snowpassword']
        Snow_url = credential['snowhost']
        print("Username : ",username)
        print("password : ",password)
        print("SNOW_URL : ",Snow_url) 
        url = Snow_url + "/api/now/attachment/upload"
        headers = {"Accept":"*/*"}
        # data = open('C:\\temp\\'+ attachment_file_name + '.csv', 'rb').read()
        data = file_content
        print("data : ",data)
        payload = {'table_name':'change_request', 'table_sys_id': sys_id}
        files = {'file': (attachment_file_name, file_content, 'text/csv', {'Expires': '0'})}

        user = 'comsappuser.gtc2'
        pwd = 'gtc2'
        response = requests.post(url, auth=(username, password), headers=headers, files=files, data=payload)
#         response = requests.request("POST", url, headers=headers, data = data, auth = (user, pwd), verify=True)
        print("response : ",response)
        if ((response.status_code == 200) or (response.status_code == 201)):
            print("response : ",response)
            cr = response.text  
            print(cr)          
        else:
            cr = "CR CANNOT BE placed"
            error = response.text
            return error
        return cr
    except:
        error = sys.exc_info()
        return error

def fetch_account_name():
    try:
        account_name = boto3.client('iam').list_account_aliases()['AccountAliases'][0]
    except: 
        print(PrintException())
        account_name = ""
    return account_name    

def get_item_dynamoDB(patchJob_ids):
    try:        
        old_changes = {}
        dynamodb = boto3.resource('dynamodb', region_name=region)
        patch_table = dynamodb.Table('Ft_dxcms_patching_e2e_automation')
        for attributeKeyValue in patchJob_ids:
            response = patch_table.get_item(Key={'patchJob_id': attributeKeyValue})
            print(response['Item'])
            #print(response['Item']['change_request'])
            old_changes[attributeKeyValue] = response['Item']['change_request']
    except:
        print(PrintException())
    return old_changes
        
def update_old_changes(old_change_ids):
    try:
        print("updating old change requests")
    
    except:
        print(PrintException())



def lambda_handler(event, context):
    try:
        global S3_Folder_Name,region
        region = event['region']
        S3_Bucket = event['S3_Bucket']
        S3_directory_name = event['S3_directory_name']
        S3_Folder_Name = event['S3_Folder_Name']
        OldTagValues = event['OldTagValues']
        TagValues = event['TagValues']
        secret = get_secret()
        change_requests = {}
        TagValues,patch_start_date,patch_end_date,Tagvalue_with_grp_name,patchJob_ids = read_data_from_config_file(S3_Bucket,S3_directory_name,TagValues)
        start_time, end_time = convert_time(patch_start_date,patch_end_date)
        # url = read_ssm_parameter(Snow_url)
        # print("SNOW URL : ",url)
        company_value,assignment_group_value,sys_id_value,category_value,CI_value,impact,priority,change_plan,implementation_plan,backout_plan,test_plan,description,urgency,type,short_description,risk = fetch_reference_cr(secret)
        # print("SNOW_URL : ",url)
        print("START TIME : ", start_time)
        print("END TIME :", end_time)
        account_name = fetch_account_name()
        for i in range(len(start_time)):
            body["company"] = company_value
            body["assignment_group"] = assignment_group_value
            body["end_date"] = end_time[i]
            body["start_date"] = start_time[i]
            body["justification"] = str(account_name + "_" + TagValues[i])
            body["category"]=category_value
            body["cmdb_ci"]=CI_value
            body["impact"]=impact
            body["priority"]=priority
            body["change_plan"]=change_plan
            body["implementation_plan"]=implementation_plan
            body["backout_plan"]=backout_plan
            body["test_plan"]=test_plan
            body["description"]=description
            body["urgency"]=urgency
            body["type"]=type
            body["short_description"]=short_description
            body["risk"]=risk
            cr_response = creat_change_request(body,secret)
            CR_Response_json_formatted = json.loads(cr_response)
            # print(cr_response)
            Change_request_no = CR_Response_json_formatted["result"]['number']['value']
            print("Change_request_no : ",Change_request_no)
            Change_request_state = CR_Response_json_formatted["result"]['state']['display_value']
            print("Change_request_state : ",Change_request_state)
            change_requests[Tagvalue_with_grp_name[i]] = Change_request_no
            file_content = encode_csv_to_base(S3_Bucket,S3_directory_name,patchJob_ids[i],Tagvalue_with_grp_name[i])
            attachment_file_name = 'PatchServerList_' + Tagvalue_with_grp_name[i]
            file_attachment_status = attch_file_to_CR(attachment_file_name,file_content,secret,sys_id_value)
            print("file_attachment_status : ",file_attachment_status)
        print("change_Requests: ",change_requests)
        update_config_file(S3_Bucket,S3_directory_name,change_requests)
        attribute_value = list(change_requests.values())
        call_update_dynamodb_lambda_function(patchJob_ids,"change_request",attribute_value)
        
        #Get old change_request numbers
        old_patchJob_ids = list(OldTagValues.values())
        old_change_requests = get_item_dynamoDB(old_patchJob_ids)
        if old_change_requests: 
            print("Old Change Requests:", old_change_requests)
            event['OldChangeRequests'] = old_change_requests
        
        
        return event
    except:
        error = PrintException()
        print(error)
    

    

event1 = {
  "OldTagValues": {
    "DEV-JUN_30_2023_15_0_4HRS": "patchJobId_fa844949-1a3d-11ee-9a9b-d74ac618a13f",
    "PROD-JUN_30_2023_15_0_3HRS": "patchJobId_fba11e3d-1a3d-11ee-b948-d74ac618a13f"
  },
  "TagValues": [
    "DEV-JUN_30_2023_10_0_4HRS",
    "PROD-JUN_30_2023_10_0_3HRS"
  ],
	"S3_Bucket": "dxcms.patchingautomation.567529657087.eu-west-3",
	"S3_directory_name": "JUN_2023/eu-west-3",
    "File_prefix": "PatchServerList",
	"S3_Folder_Name": "patching_reports",
	"region": "eu-west-3",
    "Snow_Integration_Status": "ON"
}
    
if __name__ == "__main__":
    lambda_handler(event1,"")
