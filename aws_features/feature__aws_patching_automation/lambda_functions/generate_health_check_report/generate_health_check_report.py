'''
This Lambda script execute low level health check scripts for Windows and Linux
based on the configuration file and generates csv output and store into S3 bucket
'''

import boto3
import sys,os
import csv
import json
import codecs
import botocore
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))


s3_client = boto3.client('s3',config=config)
s3_resource = boto3.resource('s3')

SSM_CW_Log_Group = os.environ['SSM_CWLogGroup_Name']
#SSM_CW_Log_Group = '/aws/ssm/dxc_pa_ssm_stdout'

def PrintException():
    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    captureErr = "Line No. : " + str(lineno)  + " | ERROR: " + str(exc_obj)
    return captureErr


# def fetch_output_from_s3(S3_Bucket,itemname):
#     try:
#         s3 = boto3.resource('s3')
#         obj = s3.Object(S3_Bucket, itemname)
#         body = obj.get()['Body'].read().decode("utf-8")
#         output = str(body)
#         print(output)
#         return output
#     except:
#         print(PrintException())

def fetch_stdout_from_CW(log_stream_name):
    try:
        CW_client = boto3.client('logs',config=config)
        print("log_stream_name : ",log_stream_name)
        response = CW_client.get_log_events(logGroupName = SSM_CW_Log_Group,logStreamName = log_stream_name)
        stdout = response['events'][0]['message']
        return stdout
    except botocore.exceptions.ClientError as error:
        if error.response['Error']['Code'] == 'ResourceNotFoundException':
            print("NO LOG EXIST")
            return "no_log_exist"
    except:
        print(PrintException())

def write_into_csv_file(S3_Bucket,S3_directory_name,health_check,instance_id,itemname,platform,instance_name):
    try:
        print(itemname)
        rows = []
        #tagValue_for_output_folder = TagValues.split("_BY")[0]
        health_check_output = fetch_stdout_from_CW(itemname)
        health_check_outputs = health_check_output.split("\n")
        for output in health_check_outputs:
            row = output.split(',')
            rows.append(row)
        
        #print("rows : ", rows)
        local_folder = '/tmp/' + health_check + '_' + instance_id + '.csv'
        with open(local_folder, 'w', newline = '') as csvfile: 
            csvwriter = csv.writer(csvfile) 
            csvwriter.writerows(rows)
            
        S3_Bucket = s3_resource.Bucket(S3_Bucket)
        directory_name = S3_Folder_Name + "/" + 'PATCHING/' + S3_directory_name+ '/HealthCheckOutupts/' + TagValues + "/" + Phase
        local_file = health_check + '_' + instance_id + '.csv'
        s3Key = directory_name + "/" + local_file
        S3_Bucket.upload_file(local_folder, s3Key)
        print(f"Health check output is processed for {instance_id }and uploaded into S3 - {s3Key}")
    except:
        print(PrintException())
        
def read_csv_from_s3(S3_Bucket,S3_directory_name,TagValues):
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

def get_tag_value(instance_id):
    ec2instance = ec2.Instance(instance_id)
    for tags in ec2instance.tags:
        if tags["Key"] == 'Name':
            instancetagvalue = tags["Value"]
    return instancetagvalue


def fetch_data_from_config_file(S3_Bucket,S3_directory_name,Phase):
    try:
        #tagValue_for_config = TagValues.split("_BY")[0]
        #directory_name = "PATCHING/" + S3_directory_name + "/Health_Check_Config_File/Health_Check_" + TagValues +".json"
        directory_name = S3_Folder_Name + "/" + "PATCHING/" + S3_directory_name + "/HealthCheck_SSM_CommandIDs/" + Phase + "_HC_SSM_CommandIDs_" + TagValues +".json"
        print("Directory Name to fetch Config File : ",directory_name)
        response = s3_client.get_object(Bucket=S3_Bucket, Key= directory_name)
        content = response['Body']  
        #data = content.read().decode("utf-8")   
        jsonObject = json.loads(content.read())
        return jsonObject
    except:
        print(PrintException())

def fetch_s3_objects(itemname):
    try:
        response = s3_client.list_objects_v2(
                Bucket = S3_Bucket,
                Prefix = itemname
            )
        s3_key = response['Contents'][0]['Key']
    except:
        s3_key = ""
    return s3_key


def call_update_dynamodb_lambda_function(patchJob_id):
    lambda_client = boto3.client('lambda',config=config)
    dynamo_event = {'patchJob_id': patchJob_id,'attribute_name':'pre_health_check_status','attribute_value':'completed'}
    response = lambda_client.invoke(
        FunctionName='dxcms-pa-lam-update-dynamodb',
        Payload=json.dumps(dynamo_event)
    )

def lambda_handler(event, context):
    try:
        global TagValues,S3_Bucket,S3_directory_name,Phase,S3_Folder_Name,region,ec2_client,ec2
        TagValues = event['PatchInstallOn']
        S3_Bucket = event['S3_Bucket']
        S3_directory_name = event['S3_directory_name']
        Phase = event["Phase"]
        S3_Folder_Name = event["S3_Folder_Name"]
        region = event["region"]

        ec2_client = boto3.client('ec2', region_name=region,config=config)
        ec2 = boto3.resource('ec2', region_name=region)

        Config_file_data = fetch_data_from_config_file(S3_Bucket,S3_directory_name,Phase)
        print("Config file Data is : ", Config_file_data)
        for i in range(len(Config_file_data)):
            print("Entering the for loop =========")
            health_check_dic_data =  Config_file_data[i]
            command_id = health_check_dic_data['command_id']
            instance_id = health_check_dic_data['Instance_id']
            health_check = health_check_dic_data['health_Check']
            Platform = health_check_dic_data['Platform']  
            #Os_name = read_csv_from_s3(S3_Bucket,S3_directory_name,TagValues)
            for instanceId in instance_id:
                i = 0
                if Platform == 'Windows':
                    # S3_key = S3_Folder_Name + "/" + "PATCHING/" + S3_directory_name + "/Outputs/" + Phase + "_HealthCheck/"
                    # itemname = S3_key + command_id + "/" + instanceId + "/awsrunPowerShellScript/0.awsrunPowerShellScript/stdout"
                    # s3_object = fetch_s3_objects(itemname)
                    itemname = command_id + "/" + instanceId + "/aws-runPowerShellScript/stdout"
                    is_log_exist = fetch_stdout_from_CW(itemname)
                    if is_log_exist != "no_log_exist" :
                        instance_name = get_tag_value(instanceId)
                        write_into_csv_file(S3_Bucket,S3_directory_name,health_check,instanceId,itemname,Platform,instance_name)
                    else:
                        print("LOG DOES NOT EXIST for : ", instanceId)
                if Platform == "Linux":
                    # S3_key = S3_Folder_Name + "/" + "PATCHING/" + S3_directory_name + "/Outputs/" + Phase + "_HealthCheck/"
                    # itemname = S3_key + command_id + "/" + instanceId + "/awsrunShellScript/0.awsrunShellScript/stdout"
                    # s3_object = fetch_s3_objects(itemname)
                    itemname = command_id + "/" + instanceId + "/aws-runShellScript/stdout"
                    is_log_exist = fetch_stdout_from_CW(itemname)
                    if is_log_exist != "no_log_exist" :
                        instance_name = get_tag_value(instanceId)
                        write_into_csv_file(S3_Bucket,S3_directory_name,health_check,instanceId,itemname,Platform,instance_name)
                    else:
                        print("LOG DOES NOT EXIST for : ", instanceId)
                i = i + 1
        patch_job_id = S3_directory_name.split('/')[2]      
        call_update_dynamodb_lambda_function(patch_job_id)
        return event
    except:
        print(PrintException())

        


if __name__ == "__main__":
    event1 = {
        "Status": "completed",
        "Count": 9,
        "PatchInstallOn": "WIN_TEST-NOV_21_2021_13_30_4HRS",
        "S3_Bucket": "dxc",
        "S3_directory_name": "NOV_2021/ap-south-1/patchJobId_90963df6-46b9-11ec-b2db-8c8caa2990d1",
        "S3_Folder_Name" : "test",
        "Phase": "post"
    }

    lambda_handler(event1, "")

    # event1 = {"Status": "completed","Count": 9,"PatchInstallOn": "DEV-JUL_25_2021_14_0_5HRS","S3_Bucket": "dxc","S3_directory_name":"JUL_2021/ap-south-1/patchJobId_7b69f86a-c86b-11eb-a4e3-32b48c8337c9","Phase": "post"}
    
#   event1 = {
#     "Status": "completed",
#     "Count": 9,
#     "PatchInstallOn": "WIN_TEST-NOV_21_2021_13_30_4HRS",
#     "S3_Bucket": "dxc",
#     "S3_directory_name": "NOV_2021/ap-south-1/patchJobId_90963df6-46b9-11ec-b2db-8c8caa2990d1",
#     "S3_Folder_Name" : "test",
#     "Phase": "post"
#     } 
    
#     lambda_handler(event1, "")