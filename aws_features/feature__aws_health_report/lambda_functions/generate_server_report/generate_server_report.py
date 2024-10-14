"""
    The main purpose of this script is to list 
    all the EC2 instances with all the its information 
    and save the CSV file to S3 bucket. 

    Note: This script requires EC2 instances to 
          be in running state and have SSM 
          connection established.

    Input Example: {"S3_Bucket":"bucket-for-testing-221", "S3_directory_name":"feature_aws_health_checks/"}
"""

import csv
import os
import boto3
import sys
import json
import uuid
import time
from datetime import datetime
from botocore.config import Config


config=Config(retries=dict(max_attempts=10,mode='standard'))

count = 0
uniqueID = ""
table_name = "Ft_Dxcms_Health_Report"
platform_names = []

'''
    This function will return the Line 
    number and the error that occured.
'''
def PrintException():
    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    captureErr = "Line No. : " + str(lineno)  + " | ERROR: " + str(exc_obj)
    return captureErr


def generate_unique_Id():
    print("generate_uniqueId called")
    execution_id = "healthCheckJobId_" + str(uuid.uuid1())
    return execution_id

'''
    This function will initialize platform_name list 
    with all the technology names availavle in the S3 bucket
'''
def initialize_platform_names(bucket_name, prefix):
    global platform_names
    client = boto3.client('s3', config=config)
    technology_name = len(prefix.split("/"))
    result = client.list_objects_v2(Bucket=bucket_name, Prefix=prefix, Delimiter='/')
    for key in result['CommonPrefixes']:
        platform_names.append(key['Prefix'].split("/")[technology_name-1])
def read_ssm_parameter(ssm_parameter):
    try:
        print(ssm_parameter)
        ssm_client = boto3.client('ssm', config=config)
        ssmParameter = ssm_client.get_parameter(Name=ssm_parameter)
        os_dict = ssmParameter['Parameter']['Value']
        return os_dict
    except:
        print(PrintException())
        

def image_name(image_id):
    ec2 = boto3.client('ec2')
    response = ec2.describe_images(ImageIds=[image_id])
    description = response['Images'][0]['Description']
    AMI_location = response['Images'][0]['ImageLocation']
    print(description)
    os_parameter = "/DXC/HealthCheck/Os_Dictionary"
    os_dict = read_ssm_parameter(os_parameter)
    os_dict = eval(os_dict)
    for key in os_dict.keys():
        try:
            if ((description.lower()).find(key) != -1 or (AMI_location.lower()).find(key) != -1):
                operating_system = os_dict[key]
                return operating_system
        except:
            exception = PrintException()
            print(exception)
            put_data("image_name", "to get the name of operating_system", "Failed to get name of operating_system", exception)
    else:
        operating_system = response['Images'][0]['PlatformDetails']
        return operating_system
        
        
    
'''
    This function creates the list of all the EC2 instances 
    with there other details like Platform, OS, Instance ID etc.
'''
def get_server_list():

    account_id = boto3.client('sts', config=config).get_caller_identity().get('Account')
    try:
        account_name = boto3.client('iam', config=config).list_account_aliases()['AccountAliases'][0]
    except:
        account_name = ""
    rows = []
    
    ec2client = boto3.client('ec2', config=config)
    try:
        response = ec2client.describe_instances()
        for reservation in response['Reservations']:
            
            for instance_data in reservation['Instances']:            
                instance_id = instance_data['InstanceId']
                operating_system = instance_data['PlatformDetails']
                ami_id = instance_data['ImageId']
                platform, temp_os, PlatformVersion = ssm_platform_name(instance_id)

                if platform == -1:
                    try:
                        if operating_system == "Linux/UNIX":
                            operating_system = image_name(ami_id)
                            print("inside",operating_system)
                    except:
                        exception = PrintException()
                        print(exception)                       

                    for platfrm in platform_names:
                        try:
                            if operating_system.lower() == "sles":
                                operating_system = "suse linux"
                        except:
                            exception = PrintException()
                            print(exception)
                        if ((platfrm.lower()).find(operating_system.lower()) != -1) or ((operating_system.lower()).find(platfrm.lower()) != -1):
                            tag_creator(instance_id, platfrm)
                            platform = platfrm
                            break
                        else:
                            platform = "UnResponsive"
                else:
                    operating_system = temp_os
                                
                instance_name = '-'
                if 'Tags' in instance_data.keys():                    
                    for item in instance_data['Tags']:
                        if item['Key'] == 'Name' and item['Value'] != '':
                            instance_name = item['Value']
                
                # print(instance_id)
                # print(operating_system)

                row = [account_id, account_name, instance_id, instance_name, operating_system, platform, PlatformVersion]
                rows.append(row)

    except:
        exception = PrintException()
        print(exception)
        put_data("boto3_ec2_client", "EC2 describe_instances", "Failed to get the list of Servers", exception)

    return rows



'''
    This function is used to return 
    the right keyword for each platform
'''
def ssm_platform_name(instance_id):
    ssm = boto3.client('ssm', config=config)

    try:
        response = ssm.describe_instance_information(Filters=[{ 'Key': 'InstanceIds', 'Values': [instance_id]}])
        if len(response['InstanceInformationList'])==0:
            print('SSM Status Not Available')
            print("Instance ID: ", instance_id)
            put_data(f"Instance ID: {instance_id}", "SSM describe_instance_information", "Failed to get OS Name and Platform Version details", "")
            print("=====================================================")
            return -1, -1, "Unknown"

    except:
        exception = PrintException()
        print(exception)
        put_data("boto3_ssm_client", "SSM describe_instance_information", "Failed to get OS Name and Platform Version details", exception)
        print('Probably something is wrong with SSM connection :(')
        print("Instance ID: ", instance_id)
        print("=====================================================")
        return -1, -1, "Unknown"
        
    else:

        # platform_names = {"Red Hat":"redhat", "Windows":"windows", "SUSE":"suse", "SLES":"suse", "Ubuntu":"ubuntu", "Debian":"debian", "Linux":"linux"}

        for platform in platform_names:
            PlatForm = response['InstanceInformationList'][0]['PlatformName']
            if (PlatForm.lower() == "sles"):
                PlatForm ="suse linux"
                
            
            if PlatForm.lower().find(platform.lower()) != -1:
                tag_creator(instance_id, platform)
                return platform, response['InstanceInformationList'][0]['PlatformName'], response['InstanceInformationList'][0]['PlatformVersion']
        put_data(f"Instance ID: {instance_id}", "Identifying the Platform/Technology name", "Failed to identify the Platform/Technology name", "")
        return "UnResponsive", response['InstanceInformationList'][0]['PlatformName'], response['InstanceInformationList'][0]['PlatformVersion']


'''
    This function is creating tags to 
    EC2 instances based on the technology name
'''
def tag_creator(instance_id, tag_name):

    print("tag_creator Called")
    client=boto3.client('ec2', config=config)
    tag_name = tag_name.replace(" ", "_")
    tags = [{
        "Key" : "DXC_healthCheck", 
        "Value" : f"hc-{tag_name}"
    }]
    status = False
         
    try:
        response = client.create_tags(
            Resources = [instance_id],
            Tags= tags
        )
        # print(response)
        print("Instance ID: ", instance_id)
        print("Added Tag: "+ str(tags))
        status = True
        # time.sleep(15)
    except:
        print(PrintException())
        print("Error occurred While Adding tags")
    
    return status


'''
    This function takes file uri and rows that needs 
    to be added and then creates the CSV file for it.
'''
def create_server_list_report(local_file_uri, rows): 

    filename = local_file_uri
    headers = ['Account Number', 'Account Name', 'Instance ID', 'Instance Name', 'Operating System', 'Technology', 'Platform Version']

    try:
        with open(filename, 'w', newline='') as csvfile: 
            csvwriter = csv.writer(csvfile) 
            csvwriter.writerow(headers) 
            csvwriter.writerows(rows)
    except:
        exception = PrintException()
        print(exception)
        put_data("server_report Creation", "Create server_report", "Failed to create server_report", exception)


'''
    This function upload the given file uri to 
    the S3 bucket and at particular key loacation provided.
'''
def upload_file(bucket_name, bucket_key, local_uri):
    print("upload_file Called")
    s3 = boto3.resource('s3', config=config)
    try:
        #print(file_uri)
        s3.meta.client.upload_file(local_uri, bucket_name, bucket_key)
        print("File Saved at: "+ bucket_key)
        return True
    except:
        exception = PrintException()
        print(exception)
        put_data("S3 Bucket", "Upload server_report", "Failed to Upload server_report", exception)
        print("================================")
        print("Unable to CSV File:"+ local_uri)
        print("Uri Used: "+ bucket_key)
        print("================================")
    
    return False


# def put_data(ResourceName, TaskName, Result, exception):

#     print("put_backup_data called")
#     global count
#     count = count + 1
#     now = datetime.now()
#     dynamodb_resource = boto3.resource('dynamodb',config=config)
#     table = dynamodb_resource.Table(table_name)
#     try:
#         response = table.put_item(
#         Item={ 
#                 'AWS_HealthCheck_UUI': uniqueID,
#                 'generate_server_report' : []
#                     }
                
#             )
#     except:
#         print(PrintException())
#         print("Error during table.put_item")


'''
    This function is updating the dynamoDB 
    table with the information send to it
'''
def put_data(ResourceName, TaskName, Result, Exception):
    
    print("put_data called")
    # global hc_issue_count
    #hc_issue_count = hc_issue_count + 1
    now = datetime.now()
    key_name = os.environ['AWS_LAMBDA_FUNCTION_NAME']
    dynamodb_resource = boto3.resource('dynamodb',config=config)
    table = dynamodb_resource.Table(table_name)
    
    try:  
        table.update_item(
        Key={
            'AWS_HealthCheck_UUI': uniqueID},
        UpdateExpression= f'SET {key_name} = list_append({key_name}, :obj)',
        ExpressionAttributeValues={
            ":obj": [
                    {
                        'ResourceName': ResourceName,
                        'TaskName': TaskName,
                        'Result': Result,
                        'Exception': Exception,
                        'Timestamp': now.strftime("%d/%m/%Y %H:%M:%S")
                    }
                ]}
        )
    except:
        print(PrintException())
        print("Error during table.update_item")


'''
    This function is creating 
    new record in dynamoDB 
'''
def hc_put_key(hc_name):

    print("hc_put_key called")
    dynamodb_resource = boto3.resource('dynamodb',config=config)
    table = dynamodb_resource.Table(table_name)
    try:
       response = table.put_item(
        Item={ 
                'AWS_HealthCheck_UUI': uniqueID,
                hc_name : [],
                'health_checks': {}
                    }      
            )
    except:
        print(PrintException())
        print("Error during table.put_item")


'''
    This function is used to validate 
    the token sent by stepfunction
'''
def token(event, task_token):

    sf = boto3.client('stepfunctions')
    sf_output = json.dumps(event)
    # task_token = event['token']

    sf_response = sf.send_task_success(
        taskToken=task_token,
        output=str(sf_output)
    )

    return sf_response


def lambda_handler(event,context):
    
    print("Event Received: ", event)
    task_token = event['token']
    event = event["Payload"]
    
    global uniqueID
    uniqueID = generate_unique_Id()
    event["uniqueID"] = uniqueID
    hc_put_key(os.environ['AWS_LAMBDA_FUNCTION_NAME'])
    bucket_name = event["S3_Bucket"]
    initialize_platform_names(bucket_name, f"{event['S3_directory_name']}aws_server_health_check/aws_health_check_low_level_scripts/")

    file_name = 'server_list_report.csv'
    bucket_key = event["S3_directory_name"]+"inventory/"
    
    local_uri = '/tmp/'

    rows = get_server_list()
    create_server_list_report(local_uri+file_name, rows)

    if upload_file(bucket_name, bucket_key+file_name, local_uri+file_name):
        return token(event, task_token)
        #return event


if __name__ == "__main__":
    event1 = {"S3_Bucket":"bucket-for-testing-221", "S3_directory_name":"abc def/"}   
    lambda_handler(event1, "")