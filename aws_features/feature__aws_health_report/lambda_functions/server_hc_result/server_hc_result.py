"""
        The purpose of this script is to generate 
        the Health Check result of all the Health 
        Check performed.

        Input Example: {"S3_Bucket":"bucket-for-testing-221", "S3_directory_name":"feature_aws_health_checks/"}
"""

import yaml
import json
import boto3
import csv
import sys
import os
from datetime import datetime
from botocore.config import Config


config=Config(retries=dict(max_attempts=10,mode='standard'))

uniqueID = ""
# table_name = "AWS_HealthCheck"
table_name = os.environ['table_name']
perform_server_hc_arn = os.environ['perform_server_hc_arn']

s3 = boto3.resource('s3', config=config)


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




def health_check_result(bucket_name, key, platform):
        # config=config(yaml_file) 
        yaml_uri = key+ "aws_health_check_low_level_scripts/"+ platform+ "/health_check_config_"+ platform +".yml"

        try:
            response = boto3.client('s3', config=config).get_object(Bucket=bucket_name, Key= yaml_uri)
            data = yaml.safe_load(response["Body"])
        except:
            exception = PrintException()
            print(exception)
            put_data("S3 Bucket", "Loading OS Config file", f"Failed to load OS Config file. Key Used: {yaml_uri}", exception)
        else:
            account_name = str(data['Account_Name'])
            technology = str(data['Technology']).lower().replace(" ", "_")
            version = str(data['Version'])
            result_file_name = f"Dorm_HC-{str(data['Technology'])}.txt"
            masterServer_outputpath = data["Output"]["Path"]["Master_Server_Output_path"]

            if masterServer_outputpath == None:
            #        masterServer_outputpath = R"C:/Users/akushwaha25/OneDrive - DXC Production/Desktop/"
                   masterServer_outputpath = "/tmp/"

            hc_filename = masterServer_outputpath + result_file_name


        try:
            if os.path.isfile(hc_filename):

                print(f'Cleaning the content of health check result file {hc_filename}')
                hc_File = open(hc_filename, 'r+')
                hc_File.truncate(0)
                        
            else:
                print(f'Health check result file has been created with --{hc_filename}')
                hc_File =  open(hc_filename, 'a+')
                        
        except:
                e = sys.exc_info()[1]
                put_data("Lambda Script", f"Opening {result_file_name} file to write", "Failed to open the file", e)
                print("Failed with ErrorException -- " + str(e))
                sys.exit()


        '''
                This function will create the textfile
                whose content will be used as a emailbody.
        '''
        def generate_healtcheck_emailbody(check_id,result_tag,comments,hostname_list):
                
            try:
                now = datetime.now()
                message = f'Check Result:{check_id}~~~{result_tag}~~~{comments}:{hostname_list}~~~{now.strftime("%Y-%m-%d %H:%M:%S")}\n'
                hc_File.write(message)

                if data["Mail"]["Secure_Mode"]["Enable"]:
                        
                        print("=> Secure Mode")
                        # hc_File.write(data["Mail"]["Secure_Mode"]["Classification_Text"]+message)

                elif data["Mail"]["Test_Mode"]:
                        print("=> Test Mode")
                        # hc_File.write('[TEST]'+message)

                else:
                        print("=> Normal Mode")
                        # hc_File.write(message)
            except:
                exception = PrintException()
                print(exception)
                put_data("Lambda Script", f"Writing in {result_file_name} file", f"Failed to write in result file", exception)
                        


        excluded_instance = []
        for health_check in data['DORM_Health_Checks']:

            check_id = str(health_check['Check_Id'])
            for sub_check in health_check['Sub_Checks']:
                hc_name = str(sub_check['Name'])

                if sub_check['Exclusion_List'] != None:
                    excluded_instance.extend(sub_check['Exclusion_List'].replace(" ", "").split(","))

                try:
                    file_name = str(f"{platform}-{hc_name}.csv").replace(" ", "_")
                    output_uri = key+"aws_health_check_processed_data_output/"+ file_name
                    s3_object = s3.Object(bucket_name,  output_uri)
                    raw_data = s3_object.get()['Body'].read().decode('utf-8').splitlines()
                    print(output_uri)
                except:
                    print(PrintException())
                    print("File Not Found")
                    print("File Name: "+ output_uri)
                    continue
                    
                else:     
                    # Result = csv_file_reader(csv.reader(data))
                    # print(check_id)
                    failed_ids = []
                    passed_ids = []
                    flag = 'Pass'
                    rows = csv.reader(raw_data)
                    header = next(rows)
                    Id= header.index('Instance_ID')
                    index= header.index('Result')
                    for row in rows:
                
                            if (str(row[index]) in ['FAIL', 'FAILED_TO_EXECUTE', 'UNREACHABLE']):
                                    # print(row[Id])
                                    failed_ids.append(row[Id])
                                    passed_ids.append(row[Id])
                                    flag = 'Fail'
                            elif (str(row[index]) in ['PASS', 'EXCLUDED']):
                                    passed_ids.append(row[Id])

                    failhostslist = str(set(failed_ids)).replace("'","")[1:-1]
                    checkedhostslist = str(set(passed_ids)).replace("'","")[1:-1]
                    print("Failed IDs:   ",failed_ids)
                    # failhostslist = sorted(set(failed_ids))
                    # failedhosts = ','.join(failhostslist)

                    if flag == "Fail":
                        if data["Mail"]["Secure_Mode"]["Enable"]:
                            failed_instance_count = f"{str(len(failhostslist.split(',')))} servers/device(s)"
                            generate_healtcheck_emailbody(check_id,'Fail', hc_name + " failed on ", failed_instance_count)
                        else:
                            generate_healtcheck_emailbody(check_id,'Fail', hc_name + " failed on following servers/device(s)", failhostslist)
                    else:
                            generate_healtcheck_emailbody(check_id,'Pass', hc_name + " check on all servers/devices is healthy","")

        # Converting to set in order to remove duplicate instances id
        excluded_instance = str(list(set(excluded_instance)))[1:-1]

        if data["Mail"]["Secure_Mode"]["Enable"]:
            if data["Mail"]["Consolidation_Counter"] and data["Mail"]["Consolidation_Counter"] != 'NA':
                general_details = f'\nConsolidation_Counter: {data["Mail"]["Consolidation_Counter"]}\nPackage Name: {technology}\nScript Version: {version}\nConfig Version: {version}'
            else:
                general_details = f'\nPackage Name: {technology}\nScript Version: {version}\nConfig Version: {version}'
        else:
            if data["Mail"]["Consolidation_Counter"] and data["Mail"]["Consolidation_Counter"] != 'NA':
                general_details = f'\nHost Server: {perform_server_hc_arn}\nConsolidation_Counter: {data["Mail"]["Consolidation_Counter"]}\nServers\Devices Checked: {str(checkedhostslist)}\nServers\Devices Excluded: {str(excluded_instance)}\nPackage Name: {technology}\nScript Version: {version}\nConfig Version: {version}'
            else:
                general_details = f'\nHost Server: {perform_server_hc_arn}\nServers\Devices Checked: {str(checkedhostslist)}\nServers\Devices Excluded: {str(excluded_instance)}\nPackage Name: {technology}\nScript Version: {version}\nConfig Version: {version}'

        hc_File.write(general_details)
        hc_File.close()
        upload_status_report(hc_filename, bucket_name,  key+ "aws_health_check_result/" + result_file_name)



'''
        This function is reading JSON file from S3 bucket 
        and for each OS platform it is calling the 
        health_check_result function for the creation for 
        Result text file.
'''
def custom_json_reader(bucket_name, key):
    print("custom_json_reader Called")

    try:
        json_uri = key+ 'inventory/health_check_config_file.json'
        content_object = s3.Object(bucket_name, json_uri)
        file_content = content_object.get()['Body'].read().decode('utf-8')
        json_content = json.loads(file_content)
        #print(json_content)
    except:
        exception = PrintException()
        print(exception)
        put_data("S3 Bucket", "Locating JSON Config file", f"Failed to locate JSON Config file. JSON Key: {json_uri}", exception)
        print("================================")
        print("Unable to get JSON File:"+ json_uri)
        print("Bucket Used: "+bucket_name)
        print("================================")
    
    else:
        try:         
            for platform in json_content:
                print(platform)
                health_check_result(bucket_name, key+ "aws_server_health_check/", platform)
        except:
            exception = PrintException()
            print(exception)
            put_data("S3 Bucket", "Reading JSON Config file", "Failed to read JSON Config file", exception)
            print("================================")
            print("Unable to Traverse JSON Data")
            print("JSON Data: "+str(json_content))
            print("================================")


'''
    This function takes file uri, fields and rows that needs 
    to be added and then creates the CSV file for it.
'''
def upload_status_report(file_uri, bucket_name, key):
    print("upload_status_report called")
    try:
        print("filename: ", file_uri)
        s3 = boto3.resource('s3', config=config)
        s3.meta.client.upload_file(file_uri, bucket_name, key)
    except:
        exception = PrintException()
        print(exception)
        put_data(f"Processed HealthCheck file: {file_uri}", "Uploading Result file", "Failed to Upload Result file", exception)
        print("Bucket Name: ", bucket_name)
        print("Key :", key)
    else:
        print("Successfully Uploaded")


def put_data(ResourceName, TaskName, Result, Exception):
    
    print("put_data called")
    now = datetime.now()
    key_name = os.environ['AWS_LAMBDA_FUNCTION_NAME']
    dynamodb_resource = boto3.resource('dynamodb', config=config)
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


def hc_get_data(key_name):
    print("hc_get_data called")
    try:
        dynamodb = boto3.resource('dynamodb',config=config)
        table = dynamodb.Table(table_name)
        response = table.get_item(TableName=table_name, Key={'AWS_HealthCheck_UUI':uniqueID})
        if key_name not in response['Item']:
            print(f"Unable to find {key_name} key")
            hc_put_key(key_name)
    except:
        print(PrintException())


def hc_put_key(hc_name):

    print("hc_put_key called")
    dynamodb_resource = boto3.resource('dynamodb',config=config)
    table = dynamodb_resource.Table(table_name)
    try:
        response = table.update_item(
        Key={
            'AWS_HealthCheck_UUI': uniqueID},
            UpdateExpression=f'SET {hc_name} = :obj',
            ExpressionAttributeValues={":obj": []}
            )
    except:
        print(PrintException())
        print("Error during table.put_item")


def token(event, task_token):

    sf = boto3.client('stepfunctions')
    sf_output = json.dumps(event)
    # task_token = event['token']

    sf_response = sf.send_task_success(
        taskToken=task_token,
        output=str(sf_output)
    )

    return sf_response


def lambda_handler(event, context):
    # TODO implement
    print("Event Recieved: ", event)
    #hc_get_data(os.environ['AWS_LAMBDA_FUNCTION_NAME'])
    try:
        task_token = event['token']
        event = event["Payload"]

        global uniqueID
        uniqueID = event["uniqueID"]
        hc_get_data(os.environ['AWS_LAMBDA_FUNCTION_NAME'])
        custom_json_reader(event['S3_Bucket'], event["S3_directory_name"])
  
    except:
        exception = PrintException()
        print(exception)
        put_data("", "", "Something went wrong", exception)


#     return event
    return token(event, task_token)


if __name__ == "__main__":
    event1 = {"S3_Bucket":"bucket-for-testing-221", "S3_directory_name":"feature_aws_health_checks/"}   
    lambda_handler(event1, "")