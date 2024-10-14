'''
This lambda script is used to stop the instances which got started to perform patch scanning.
'''

import boto3
import json,sys
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))
   
def PrintException():
    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    captureErr = "Line No. : " + str(lineno)  + " | ERROR: " + str(exc_obj)
    return captureErr

def read_item_dynamoDB(patchJob_id):
    dynamodb = boto3.resource('dynamodb')
    patch_table = dynamodb.Table('Ft_dxcms_patching_e2e_automation')

    try:
        response = patch_table.get_item(Key={'patchJob_id': patchJob_id})
        itemsFromTable = response['Item']
        
        stoppedStateInstances = itemsFromTable["stopped_state_instances"]
        print("Stopped State Instances are : ",stoppedStateInstances)
        return stoppedStateInstances
    except:
        print(PrintException())
        

def stop_instances(ec2_instance_ids):
    try:
        ec2_client = boto3.client('ec2',region_name = region,config=config)    
        response = ec2_client.stop_instances( InstanceIds=ec2_instance_ids)
    except:
        print(PrintException())
        
def lambda_handler(event, context):
    try:
        global tagValue,S3_Bucket,S3_directory_name,local_folder
        global patchInstallStatusOfInstances,region

        tagValues = event['TagValues']
        S3_Bucket = event['S3_Bucket']
        S3_directory_name = event['S3_directory_name']
        region = event['region']
        patchMonth = S3_directory_name.split("/")[0]
        # region = S3_directory_name.split("/")[1]
        patchJob_id = S3_directory_name.split("/")[1]
        
        stoppedStateInstances = read_item_dynamoDB(region)
        if stoppedStateInstances == [] or stoppedStateInstances == None:
            print("No Instances to stop...")
        else:
            stop_instances(stoppedStateInstances)
        print("Instances are stopped successfully")
        # stop_instances(stoppedStateInstances)
        # print("Instances are stopped successfully")
        return event
        
    except:
        print(PrintException())

if __name__ == "__main__":
    event1 =  {"TagValues": ["WIN_TEST-JAN_24_2022_13_30_4HRS","RHEL_TEST-FEB_7_2022_11_15_5HRS"],"S3_Bucket": "dxc","S3_directory_name": "JUN_2021/ap-south-1/patchJobId_98d80322-c0a9-11eb-b95e-5f544c2b0dea","region":"ap-south-1"}
    lambda_handler(event1, "")     
