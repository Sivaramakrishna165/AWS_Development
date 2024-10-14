'''
This Lambda script creates downtime tag on instances by taking input from CSV files.
It also takes Patch Group and Reboot as input from the CSV and adds the Patch Group and Reboot tags to the instances.
'''

import boto3
from botocore.client import Config
import codecs
import json
import csv
import os
import sys
from datetime import datetime, time
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))

ssm_parameter = os.environ['Patching_Type'] #'/DXC/PatchingAutomation/Patching_Type'

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
        snow_integation_status = ssmParameter['Parameter']['Value']
        return snow_integation_status
    except:
        print(PrintException())

def upload_file_into_s3(bucket_name,output_local_file_path,output_s3_key_file_path):
    try:
        s3_resource = boto3.resource('s3', config=Config(signature_version='s3v4'))
        bucket = s3_resource.Bucket(bucket_name)
        Key = output_s3_key_file_path
        print("Key : ", Key)
        print("fileFullName_Local : ",output_local_file_path)
        bucket.upload_file(output_local_file_path, Key)
    except:
        print(PrintException())
       
def write_csv_file(row):
    try:
        with open(local_output_file_path, 'a', newline='') as csvfile:
            filewriter = csv.writer(csvfile, delimiter=',')        
            filewriter.writerow(row)
    except:
        print(PrintException())

def update_tag(*argv):
    try:
        instance_id,tag_key,tag_value,day,week,month,hour,minute,duration,tag_key2,tag_value2,tag_key3,tag_value3 =  argv
        #Add tags to ec2 instances
        response = client.create_tags(    
            Resources=[
                instance_id,
            ],
            Tags=[
                {
                    'Key': tag_key,
                    'Value': tag_value
                },
                {
                    'Key': tag_key2,
                    'Value': tag_value2
                },
                {
                    'Key': tag_key3,
                    'Value': tag_value3
                },
            ]
        )
        row_to_add = [instance_id,day,week,month,hour,minute,duration,tag_key,tag_value,tag_key2,tag_value2,tag_key3,tag_value3,"success","NA"]
        write_csv_file(row_to_add)
        print(f"Instance : {instance_id} - SUCCESS")
    except:
        error = PrintException()
        print(error)
        row_to_add = [instance_id,day,week,month,hour,minute,duration,tag_key,tag_value,tag_key2,tag_value2,tag_key3,tag_value3,"failed",error]
        write_csv_file(row_to_add)
        print(f"Instance : {instance_id} - FAILED")

def update_tag_on_instance(S3_Bucket, s3_file_key_path,patching_type):
    try:

        data = s3client.get_object(Bucket = S3_Bucket, Key = s3_file_key_path)

        line_count = 0
        for row in csv.DictReader(codecs.getreader("utf-8")(data["Body"])):
            instance_id = str(row["instance_id"])
            instance_id = instance_id.strip()
            day = (str(row["Day"])).strip()
            week = (str(row["Week"])).strip()
            month = (str(row["Month"])).strip()
            hour = (str(row["Hour"])).strip()
            minute = (str(row["Minute"])).strip()
            duration = (str(row["Duration"])).strip()
            patch_group = (str(row["Patch Group"])).strip()
            reboot = (str(row["Reboot"])).strip()
            if duration == 0:
                duration = '4'
            else:
                duration = str(row["Duration"])

            if instance_id != "":
                print("INSTANCE ID : ", instance_id)
                if None not in (instance_id,day,week,month,hour,minute,duration,patch_group,reboot):
                    if "" not in (instance_id,day,week,month,hour,minute,duration,patch_group,reboot):
                        downtime_window = day + " " + week + " " + month + " " + hour + " " + minute + " " + duration
                        if patching_type == 'standard_patching':
                            window = "Downtime Window"
                        else:
                            window = "Adhoc Downtime Window"
                        update_tag(instance_id,window,downtime_window,day,week,month,hour,minute,duration,"Patch Group",patch_group,"Reboot",reboot)
                    else:
                        row_to_add = [instance_id,day,week,month,hour,minute,duration,window,"","Patch Group","","Reboot","","failed","wrong format"]
                        write_csv_file(row_to_add)

                else:
                    row_to_add = [instance_id,day,week,month,hour,minute,duration,window,"","Patch Group","","Reboot","","failed","wrong format"]
                    write_csv_file(row_to_add)
    except:
        error = PrintException()
        print(error)
        row_to_add = [instance_id,day,week,month,hour,minute,duration,"Downtime Window","","Patch Group","","Reboot","","failed",error]
        write_csv_file(row_to_add)

def get_aws_account_info():
    accoundId = ""
    try:
        sts = boto3.client("sts",config=config)
        accoundId = sts.get_caller_identity()["Account"]    
    except:
        print(PrintException())
        accoundId = ""
    return accoundId

def lambda_handler(event,context):
    try:      
        global local_output_file_path, s3client, client,patching_type

        patching_type = read_ssm_parameter(ssm_parameter)
        event['patching_type'] = patching_type

        region = os.environ['AWS_REGION']
        account_id = get_aws_account_info()
        if patching_type == 'standard_patching':
            s3_bucket_name = "dxcms.patchingautomation." + account_id + "." + region
        else:
            s3_bucket_name = "dxcms.adhocpatchingautomation." + account_id + "." + region
        s3_input_file_key_path = "downtime.csv"

        now = datetime.now()
        date_time = now.strftime("%m-%d-%Y_%H-%M-%S")
        local_output_file_path = "/tmp/" + "downtime_tag_outputfile_" + date_time + ".csv"
        client = boto3.client('ec2',config=config)
        s3client = boto3.client('s3',config=config)
        output_s3_key_file_path = s3_input_file_key_path.split(".csv")[0] + "downtime_tag_outputfile_" + date_time + ".csv"
        
        #Header for csv file
        header = [ "instance_id","day","week","month","hour","minute","duration","tag_key","tag_value","tag_key2","tag_value2","tag_key3","tag_value3","status","comments" ]
        write_csv_file(header)

        #Update tags on instances and upload status of tag creation to S3 bucket
        update_tag_on_instance(s3_bucket_name,s3_input_file_key_path,patching_type)
        upload_file_into_s3(s3_bucket_name,local_output_file_path,output_s3_key_file_path)
        return event
    except:
        print(PrintException())

        
# simple test cases
if __name__ == "__main__":
    event1 = {"patching_type":"adhoc_patching/standard_patching","S3_Bucket": "dxc","s3_file_key_path": "test/downtime_tag.csv","region": "ap-south-1"}   
    lambda_handler(event1, "")