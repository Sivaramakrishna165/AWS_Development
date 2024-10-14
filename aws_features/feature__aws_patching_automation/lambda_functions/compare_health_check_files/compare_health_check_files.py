'''
This Lambda script compares the health check output files and generates the consolidated output.
'''

from platform import platform
import boto3
import csv
from botocore.utils import instance_cache
import yaml
import time
import sys
import codecs
import json
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))

s3_client = boto3.client("s3",config=config)
s3_resource = boto3.resource('s3')

def PrintException():
    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    captureErr = "Line No. : " + str(lineno)  + " | ERROR: " + str(exc_obj)
    return captureErr

# This function will return the windows_healthChecks, linux_healthChecks, and two lists which contains dictionaries of checkname,col_name 
# and conditions Windows_check_name: a list contains the healthCheck names for window instances, 
# Linux_Check_Name: a list contains the healthcheck names for linux instances,  
# Windows_sub_check: list contains dictionaries of checks for windows, 
# linux_sub_check: list caontains dictionary of checks for linux

def get_data_from_yaml_file(S3_Bucket):
    try:
        S3_Key = S3_Folder_Name + "/" + "HealthCheckConfigAndScripts/ConfigFile/healthCheckConfig.yml"
        response = s3_client.get_object(Bucket=S3_Bucket, Key=S3_Key)
        try:
            configfile = yaml.safe_load(response["Body"])
            #print(configfile)
            Windows_patch_checks = configfile['Patch_Checks'][0]
            #print(Windows_patch_checks)
            #platform_check = patch_checks['Check_Name']
            Windows_sub_check = Windows_patch_checks['Sub_Checks']
            #print(Windows_sub_check)
            Windows_check_name = [ sub['Name'] for sub in Windows_sub_check]
            Linux_patch_checks = configfile['Patch_Checks'][1]
            linux_sub_check = Linux_patch_checks['Sub_Checks']
            Linux_Check_Name = [ sub['Name'] for sub in linux_sub_check]
            print("Windows_check_name : ", Windows_check_name)
            print("Windows_sub_check : ", Windows_sub_check)
            print("linux_sub_check : ", linux_sub_check)
            print("Linux_Check_Name : ", Linux_Check_Name)
            return Windows_check_name, Linux_Check_Name,  Windows_sub_check, linux_sub_check    
        except yaml.YAMLError as exc:
            print(exc)
    except:
        print(PrintException())

def read_item_dynamoDB(patchJob_id):
    dynamodb = boto3.resource('dynamodb')
    patch_table = dynamodb.Table('Ft_dxcms_patching_e2e_automation')

    try:
        response = patch_table.get_item(Key={'patchJob_id': patchJob_id})
        itemsFromTable = response['Item']

        return itemsFromTable["patch_installed_instances"]
    except:
        print(PrintException())
        
        
def get_patching_status(instanceId,patch_type):
    try:
        status = patchInstallStatusOfInstances[instanceId]
    except:
        status = get_PatchInstallOn_tagValue(instanceId,patch_type)
    return status

def get_PatchInstallOn_tagValue(instanceId,patch_type):
    try:
        PatchInstallOnValue = ""
        client = boto3.client('ec2',region_name = region,config=config)
        ec2res = boto3.resource('ec2',region_name = region)
        instanceInfo = ec2res.Instance(id=instanceId)
        for tag in instanceInfo.tags:
            if tag['Key'] == patch_type:
                PatchInstallOnValue = tag['Value']
                
        if "BN" in PatchInstallOnValue:
            status = "Not Included-backup failed"
        elif "AN" in PatchInstallOnValue:
            status = "Not Included-stopping app failed"
        else:
            status = "Not Included into Patching-Check SSM Agent"
    except:
        print(PrintException())
    return status
    
def fetch_instance_ids(TagValues,patch_type):
    try:
        windows_instance_id = []
        linux_instance_id = []
        instanceTags = (TagValues + "*")
        response = ec2_client.describe_instances(
            Filters=[
                {
                    'Name': 'tag:'+patch_type,
                    'Values': [
                        instanceTags,
                    ]
                },
            ]
        )
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                try:
                    if instance['Platform'] == 'windows':
                        windows_instance_id.append(instance["InstanceId"])
                except:
                    linux_instance_id.append(instance["InstanceId"])
        return windows_instance_id,linux_instance_id
    except:
        print(PrintException())

def read_csv_from_s3(S3_Bucket,filePath,column):
    try:
        #directory_name = "PATCHING" + "/" + S3_directory_name + "/HealthCheck/" +  tagValue + ".csv"
        print("FILE PATH ====> ", filePath)
        data = s3_client.get_object(Bucket = S3_Bucket, Key = filePath)
        col_list = []
        for row in csv.DictReader(codecs.getreader("utf-8")(data["Body"])):
            col_list.append(row[column])
        #InstanceId_Status_dic = {instanceId[i]: status[i] for i in range(len(instanceId))}
        return col_list
    except:
        print(PrintException())

   
def get_tag_value(instance_id):
    ec2instance = ec2.Instance(instance_id)
    for tags in ec2instance.tags:
        if tags["Key"] == 'Name':
            instancetagvalue = tags["Value"]
    return instancetagvalue

def get_operating_system(S3_Bucket,S3_directory_name,TagValues):
    try:
        column = 'OperatingSystem'
        filePath = S3_Folder_Name + "/" + 'PATCHING/' + S3_directory_name + '/ServersList/PatchServerList_' + TagValues + '.csv'
        data = s3_client.get_object(Bucket = S3_Bucket, Key = filePath)
        col_list = []
        for row in csv.DictReader(codecs.getreader("utf-8")(data["Body"])):
            col_list.append(row[column])
        #InstanceId_Status_dic = {instanceId[i]: status[i] for i in range(len(instanceId))}
        return col_list
    except:
        print(PrintException())

#PATCHING/JUN_2021/HealthCheckOutupts/JUL_11_2021_8_0_5HRS/pre/uptime_i-06fc5bd182644bbd4.csv
def fetch_csv_file_for_windows_instance(S3_Bucket,S3_directory_name,TagValues,patch_type):
    try:
        window_health_check, linux_health_check, window_dic_check,linux_dic_check = get_data_from_yaml_file(S3_Bucket)
        window_instance_id, linux_instance_id = fetch_instance_ids(TagValues,patch_type)
        #OS_name = get_operating_system(S3_Bucket,S3_directory_name,TagValues)
        Status_list = []
        for j in range(len(window_instance_id)):
            instance_status = []
            instance_status.append(window_instance_id[j])
            instance_status.append("Windows")
            #OS_name = get_osname_instance(window_instance_id[j], inst_platform = 'windows')
            #instance_status.append(OS_name[j])
            #isIncludedIntoPatching = get_PatchInstallOn_tagValue(window_instance_id[j])
            #instance_status.append(isIncludedIntoPatching)
            Instance_name = get_tag_value(window_instance_id[j])
            instance_status.append(Instance_name)
            patching_status = get_patching_status(window_instance_id[j],patch_type)
            instance_status.append(patching_status)            
            
            for i in range(len(window_dic_check)):
                Health_check_name = window_dic_check[i]['Name']
                Column = window_dic_check[i]['Column_Name']
                Condition = window_dic_check[i]['Condition']
                file_name1 =  Health_check_name + "_" + window_instance_id[j] + ".csv"
                file_path1 = S3_Folder_Name + "/" + "PATCHING/" + S3_directory_name + "/HealthCheckOutupts/" + TagValues + "/pre/" + file_name1
                file_path2 = S3_Folder_Name + "/" + "PATCHING/" + S3_directory_name + "/HealthCheckOutupts/" + TagValues + "/post/" + file_name1
            
                col_list1 = read_csv_from_s3(S3_Bucket,file_path1,Column)
                print(col_list1)
                col_list2 = read_csv_from_s3(S3_Bucket,file_path2,Column)
                print(col_list2)
                status = compare_csv_files(col_list1,col_list2,Condition,Column)
                #instance_status.append(window_instance_id) 
                #instance_status.append(Health_check_name)
                instance_status.append(status)
            Status_list.append(instance_status)
        return Status_list
    except:
        print(PrintException())

def fetch_csv_file_for_linux_instance(S3_Bucket,S3_directory_name,TagValues,patch_type):
    window_health_check, linux_health_check, window_dic_check,linux_dic_check = get_data_from_yaml_file(S3_Bucket)
    window_instance_id, linux_instance_id = fetch_instance_ids(TagValues,patch_type)
    #OS_name = get_operating_system(S3_Bucket,S3_directory_name,TagValues)
    Status_list = []
    for j in range(len(linux_instance_id)):
        instance_status = []
        instance_status.append(linux_instance_id[j])
        instance_status.append("Linux")
        #OS_name = get_osname_instance(window_instance_id[j], inst_platform = 'windows')
        #instance_status.append(OS_name[j])
        #isIncludedIntoPatching = get_PatchInstallOn_tagValue(linux_instance_id[j])
        #instance_status.append(isIncludedIntoPatching)
        Instance_name = get_tag_value(linux_instance_id[j])
        instance_status.append(Instance_name)
        patching_status = get_patching_status(linux_instance_id[j],patch_type)
        instance_status.append(patching_status)
        
        for i in range(len(linux_dic_check)):
            Health_check_name = linux_dic_check[i]['Name']
            Column = linux_dic_check[i]['Column_Name']
            Condition = linux_dic_check[i]['Condition']
            file_name1 =  Health_check_name + "_" + linux_instance_id[j] + ".csv"
            file_path1 = S3_Folder_Name + "/" + "PATCHING/" + S3_directory_name + "/HealthCheckOutupts/" + TagValues + "/pre/" + file_name1
            file_path2 = S3_Folder_Name + "/" + "PATCHING/" + S3_directory_name + "/HealthCheckOutupts/" + TagValues + "/post/" + file_name1
            col_list1 = read_csv_from_s3(S3_Bucket,file_path1,Column)
            print(col_list1)
            col_list2 = read_csv_from_s3(S3_Bucket,file_path2,Column)
            print(col_list2)
            status = compare_csv_files(col_list1,col_list2,Condition,Column)
            #instance_status.append(window_instance_id) 
            #instance_status.append(Health_check_name)
            instance_status.append(status)
        Status_list.append(instance_status)
    return Status_list

            

def compare_csv_files(col1,col2,condition,Column):
    try:
        comparision_result = []
        subs = "Fail"
        for i in range(len(col1)):
            if condition == 'match':
                if col1[i] in col2:
                    comparision_result.append("Pass")
                else:
                    col_difference = set(col1).symmetric_difference(set(col2))
                    failure_string = ''.join([str(str(item)+",") for item in col_difference])
                    failure_cause = "Fail" + " ( "+ str(failure_string) + ")"
                    comparision_result.append(failure_cause)
                    #comparision_result.append("Fail" + failure_cause)
                i = i + 1
            if condition == 'le':
                if col1[i] <= col2[i]:
                    comparision_result.append("Pass")
                else:
                    # comparision_result.append("Fail")
                    Failure_Cause = "Fail" + " ( " + col1[i] + " " + Column + " <= " + col2[i] + " " + Column + " )"
                    comparision_result.append(Failure_Cause)
                i = i + 1
            if condition == 'ge':
                if col1[i] >= col2[i]:
                    comparision_result.append("Pass")
                else:
                    Failure_Cause = "Fail" + " ( " + col1[i] + " " + Column + " >= " + col2[i] + " " + Column + ")"
                    comparision_result.append(Failure_Cause)
                i = i + 1
            if condition == 'lt':
                if col1[i] < col2[i]:
                    comparision_result.append("Pass")
                else:
                    Failure_Cause = "Fail" + " ( " + col1[i] + " " + Column + " < " + col2[i] + " " + Column + ")"
                    comparision_result.append(Failure_Cause)
                i = i + 1
            if condition == 'gt':
                if col1[i] > col2[i]:
                    comparision_result.append("Pass")
                else:
                    Failure_Cause = "Fail" + " ( " + col1[i] + " " + Column + " > " + col2[i] + " " + Column + ")"
                    comparision_result.append(Failure_Cause)
                i = i + 1
        if list(filter(lambda x: subs in x, comparision_result)):
            Failure_res = list(filter(lambda x: subs in x, comparision_result))
            Status = Failure_res[0]
        # if "Fail" in comparision_result:
        #     Status =  "Fail"
        else:
            Status = "Pass"
    except:
        print(PrintException())
        Status = "Fail"
    print("==============================> >>>>>>>> ", Status)
    return Status


def create_csv_file(S3_Bucket,health_check,status,Platform):
    try:
        fields = health_check
        print(fields)
        fields.insert(0,"Instance_Id")
        fields.insert(1,"Flavour")
        #fields.insert(2,"Operating_Sysytem")
        fields.insert(2,"Instance_Name")
        fields.insert(3,"Patch Installation Status")
        rows = status
        #local_folder = 'c:\\temp\\' + Platform + "_Health_Check_Validation" + '.csv'
        local_folder = "/tmp/" + Platform + "_Health_Check_Validation" + '.csv'
        with open(local_folder, 'w', newline = '') as csvfile: 
            csvwriter = csv.writer(csvfile) 
            csvwriter.writerow(fields) 
            csvwriter.writerows(rows)
        S3_Bucket = s3_resource.Bucket(S3_Bucket)
        directory_name = 'PATCHING/' + S3_directory_name+ '/HealthCheckOutupts/' + TagValues + "/validation"
        local_file = Platform + "_Health_Check_Validation" + '_' + TagValues + '.csv'
        #local_file = "Health_Check_Validation" + '.csv'
        s3Key = S3_Folder_Name + "/" + directory_name + "/" + local_file
        S3_Bucket.upload_file(local_folder, s3Key)
    except:
        print(PrintException())


def call_update_dynamodb_lambda_function(patchJob_id,attribute_name,attribute_value):
    lambda_client = boto3.client('lambda',config=config)
    dynamo_event = {'patchJob_id': patchJob_id,'attribute_name':attribute_name,'attribute_value':attribute_value}
    response = lambda_client.invoke(
        FunctionName='dxcms-pa-lam-update-dynamodb',
        Payload=json.dumps(dynamo_event)
    )

def lambda_handler(event, context):
    try:
        global TagValues,S3_Bucket,S3_directory_name,S3_Folder_Name
        global patchInstallStatusOfInstances,region,ec2_client,ssm_client,ec2
        region = event['region']
        #local_folder = "/tmp/" + "Health_Check_Validation" + '.csv'
        # local_folder = "c:\\temp\\" + "Health_Check_Validation" + '.csv'
        TagValues = event['PatchInstallOn']
        S3_Bucket = event['S3_Bucket']
        S3_directory_name = event['S3_directory_name']
        S3_Folder_Name = event['S3_Folder_Name']
        Patching_Type= event['Patching_Type']
        if Patching_Type == 'Adhoc':
            patch_type = 'AdhocPatchInstallOn'
        else:
            patch_type = 'PatchInstallOn'

        ec2_client = boto3.client("ec2",region_name = region,config=config)
        ssm_client = boto3.client("ssm",region_name = region,config=config)
        ec2 = boto3.resource('ec2',region_name = region)
        
        patchMonth = S3_directory_name.split("/")[0]
        region = S3_directory_name.split("/")[1]
        patchJob_id = S3_directory_name.split("/")[2]
        
        patchInstallStatusOfInstances = read_item_dynamoDB(patchJob_id)
                
        TagValues = TagValues.replace("_BY_AY","")
        #HC_SSM_CmdIds_ConfigFileName = "PATCHING/" + S3_directory_name + "/HealthCheck_SSM_CommandIDs/" + "Post_HC_SSM_CommandIDs_" + TagValues + ".json"
        
        windows_instance_id,linux_instance_id = fetch_instance_ids(TagValues,patch_type)
        print("Windows Instance IDs : ", windows_instance_id)
        print("Linux Instance IDs : ", linux_instance_id)
        if len(windows_instance_id) > 0:
            print("Working for Windows....")
            Platform = "Windows"
            window_health_check, linux_health_check, window_dic_check,linux_dic_check = get_data_from_yaml_file(S3_Bucket)
            Status = fetch_csv_file_for_windows_instance(S3_Bucket,S3_directory_name,TagValues,patch_type)
            print("Output of CSV file - Windows : ", Status)
            create_csv_file(S3_Bucket,window_health_check,Status,Platform)
        if len(linux_instance_id) > 0:
            print("Working for Windows....")
            Platform = "Linux"
            window_health_check, linux_health_check, window_dic_check,linux_dic_check = get_data_from_yaml_file(S3_Bucket)
            Status = fetch_csv_file_for_linux_instance(S3_Bucket,S3_directory_name,TagValues,patch_type)
            print("Output of CSV file - Linux : ", Status)
            create_csv_file(S3_Bucket,linux_health_check,Status,Platform)
        call_update_dynamodb_lambda_function(patchJob_id,attribute_name='post_health_check_status',attribute_value='completed')
        output = {}
        output['Patching_Type'] = Patching_Type
        output['S3_Bucket'] = S3_Bucket
        output['S3_directory_name'] = S3_directory_name
        output['PatchInstallOn'] = TagValues
        output['Patch_Phase'] = 'post-patch'
        output['S3_Folder_Name'] = S3_Folder_Name
        output['region'] = region
        return output
    except:
        print(PrintException())


if __name__ == "__main__":
    #event1 =  {"S3_Bucket": "dxc","Phase": "post","S3_directory_name": "JUN_2021/ap-south-1/patchJobId_98d80322-c0a9-11eb-b95e-5f544c2b0dea","PatchInstallOn": "DEV-JUN_20_2021_14_0_5HRS"}   
    event1 = {
      "S3_Bucket": "dxc",
      "S3_directory_name": "NOV_2021/ap-south-1/patchJobId_90963df6-46b9-11ec-b2db-8c8caa2990d1",
      "PatchInstallOn": "WIN_TEST-NOV_21_2021_13_30_4HRS",
      "Patch_Phase": "post-patch",
      "S3_Folder_Name" : "test",
      "region":"ap-south-1"
    }
    lambda_handler(event1, "")
