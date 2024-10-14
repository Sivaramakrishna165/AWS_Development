"""
    This script is creating a selfheal csv report from the dynamodb table and then 
    uploading it to S3 bucket.

    This script is part of reporting step function which is triggered weekly using an eventbridge
    rule

    It reads the items stored in dynamodb table for past 7 days, creates a csv file out of it and 
    stores the same in S3 bucket.

    Sample file location: 
    feature_aws_selfheal/Customer_sh_Data/{account_id}/{region}/<date>/selfheal_report.csv

    Sample Input: {} #no input required
"""

import boto3
import sys
import json
import os
from datetime import date, datetime
from datetime import timedelta
from csv import writer
from boto3.dynamodb.conditions import Key, Attr
from botocore.config import Config


file_uri = "/tmp/"
# file_uri = R"C:\Users\akushwaha25\OneDrive - DXC Production\Desktop\\"
table_name = os.environ['table_name']
region = os.environ['AWS_REGION']
# table_name = "selfheal_test_1"
cloudops_bucket_name = os.environ['destination_bucket_name']
# cloudops_bucket_name = "/DXC/SelfHeal/CloudOps_S3_Bucket"
customer_name_parameter = os.environ['customer_name_parameter']
# customer_name_parameter = "/DXC/Main/CustomerName"
config=Config(retries=dict(max_attempts=10,mode='standard'))
file_name = "selfheal_report.csv"
attributeList = ['AccountId', 'AccountName', 'selfHealJobId', 'CIName', 'Event', 'Event Date', 'ImpactedResourceId', 'ImpactedResourceName', 'Region', 'SelfHealDiagnosisResult', 'Resolution_Validation', 'Customer_Name']

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


'''
    This function is reading dynamoDB using filter 
    condition and then calling prepare data function
'''
def read_dynamoDB():
    print("read_dynamoDB Called")
    customer_name = read_ssm_parameter(customer_name_parameter)
    dynamodb = boto3.resource('dynamodb', config=config)
    table = dynamodb.Table(table_name)

    if os.path.isfile(file_uri+file_name):
        os.remove(file_uri+file_name)
    append_csv([attributeList])

    now = (date.today()).strftime('%FT%TZ')
    start_time = (date.today() - timedelta(days=8)).strftime('%FT%TZ')
    
    flag = False
    response = table.scan(    
                            Limit=80, 
                            FilterExpression=Key('Event Date').between(start_time,now)
                        )
    try:
        for data in response['Items']:
            data['Customer_Name'] = customer_name
            prepare_data(data)
            flag = True
    except:
        print("Error")

    while 'LastEvaluatedKey' in response:
        response = table.scan(
                                Limit=80, 
                                ExclusiveStartKey=response['LastEvaluatedKey'], 
                                FilterExpression=Key('Event Date').between(start_time,now)
                                )
        for data in response['Items']:
            data['Customer_Name'] = customer_name
            prepare_data(data)
            flag = True
        # time.sleep(5)

    return flag


'''
    This function is preparing the 
    data that will be written in csv 
    report
'''
def prepare_data(data):
    row = []
    for item in attributeList:
        value = data.get(item, "")
        if item == 'SelfHealDiagnosisResult':
            if value not in ["", {}]:
                value = "True"
            else:
                value = "False"

            row.append(value)
        else:
            
            # for key in dictt:
            #     value = dictt[key]
            #     if item == 'SelfHealDiagnosisResult':
            #         if value not in ["", {}]:
            #             value = "True"
            #         else:
            #             value = "False"

            row.append(value)

    append_csv([row])


'''
    This function append the cloudwatch data to 
    csv name given to it. If file not exist it 
    will create and add data to it. 
'''
def append_csv(rows):
    print("append_csv Called")
    
    try:
        with open(file_uri+file_name, 'a', newline='') as f_object:
            
            writer_object = writer(f_object)
            for row in rows:
                writer_object.writerow(row)
        
            f_object.close()
    except:
        exception = PrintException()
        print(exception)
        print("================================")
        print("Unable to write in a File: "+file_name+'.csv')
        print("================================")


def read_ssm_parameter(ssm_parameter):
    try:
        ssm_client = boto3.client('ssm', config=config)
        ssmParameter = ssm_client.get_parameter(Name=ssm_parameter)
        ssm_parameter_value = ssmParameter['Parameter']['Value']
        return ssm_parameter_value
    except:
        print(PrintException())


'''
    This function upload the files from the list to 
    the S3 bucket and at particular key loacation provided.
'''
def upload_status_report(bucket_name, key):
    print("upload_status_report called")
    try:
        print("filename: ", file_uri+file_name)
        s3 = boto3.resource('s3', config=config)
        s3.meta.client.upload_file(file_uri+file_name, bucket_name, key)
    except:
        exception = PrintException()
        print(exception)
        print("Bucket Name: ", bucket_name)
        print("Key :", key)
    else:
        print("Successfully Uploaded")
        print(f"Saved at: {bucket_name}/{key}")


def token(event, task_token):

    sf = boto3.client('stepfunctions', config=config)
    sf_output = json.dumps(event)
    # task_token = event['token']

    sf_response = sf.send_task_success(
        taskToken=task_token,
        output=str(sf_output)
    )
    return sf_response


def lambda_handler(event, context):
    # TODO implement
    print("Received Event: ", event)
    S3_Bucket = read_ssm_parameter(cloudops_bucket_name)
    S3_directory_name = "feature_aws_selfheal/"

    try:
        # task_token = event['token']
        # event = event["Payload"]
        
        event["S3_Bucket"] = S3_Bucket
        event["S3_directory_name"] = S3_directory_name

        read_dynamoDB()

        account_id = boto3.client('sts', config=config).get_caller_identity().get('Account')
        now = (date.today() - timedelta(days = 1))
        destination_key = f"{S3_directory_name}Customer_sh_Data/{account_id}/{region}/{now}/{file_name}"

        upload_status_report(S3_Bucket, destination_key)
        return event
        # return token(event, task_token)
    except:
        exception = PrintException()
        print("================================")
        print("Something went wrong.")
        print("Exception: ",exception)
        print("================================")
        
    
    return event
    # return token(event, task_token)


# event1 = { }

# if __name__ == "__main__":
#     lambda_handler(event1,"")

