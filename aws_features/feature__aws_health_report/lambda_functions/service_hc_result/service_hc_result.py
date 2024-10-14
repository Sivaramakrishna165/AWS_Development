"""
        The purpose of this script is to generate 
        the Health Check result of all the Health 
        Check performed.
        Input Example: {"S3_Bucket":"bucket-for-testing-221", "S3_directory_name":"feature_aws_health_checks/"}
"""

import yaml
import json
import boto3
from datetime import datetime
import csv
import sys
import logging
import os
import uuid
from botocore.config import Config


config=Config(retries=dict(max_attempts=10,mode='standard'))


s3 = boto3.resource('s3', config=config)
table_name = os.environ['table_name']


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
    This function is updating the dynamoDB 
    table with the information send to it
'''
def put_data(ResourceName, TaskName, Result, Exception):
    
    print("put_data called")
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

def health_check_result(bucket_name, key):
        utc_time = str(datetime.utcnow().replace(microsecond=0))
        yaml_uri = key+ "service_health_check_config/"+"service_health_check_config.yml"

        try:
                response = boto3.client('s3', config=config).get_object(Bucket=bucket_name, Key= yaml_uri)
                data = yaml.safe_load(response["Body"])
        except:
                Exception=PrintException()
                print(Exception)
                put_data("Configuration YAML File", "Reading configuration YAML file from S3 Bucket", "Error occurred while reading configuration file", Exception)
        else:
                result_file_name = "Dorm_HC_"+ str(data['Technology'])+ ".txt"
                print(result_file_name)
                masterServer_outputpath = data["Output"]["Path"]["Master_Server_Output_path"]
                print(masterServer_outputpath)

                if masterServer_outputpath == None:
                       masterServer_outputpath = "/tmp/"
                else:
                        masterServer_outputpath = masterServer_outputpath

                hc_filename = masterServer_outputpath + result_file_name                      
        
        Logfile = '{}DHC_Result-Logfile.log'.format(masterServer_outputpath)

        try:
                logging.basicConfig(level=logging.DEBUG,filename=Logfile,filemode='w',format='%(asctime)s:%(module)s:%(levelname)s:%(message)s',datefmt='%d/%m/%Y %I:%M:%S')
        except:
                open(Logfile, 'a')
                logging.basicConfig(level=logging.DEBUG,filename=Logfile,filemode='w',format='%(asctime)s:%(module)s:%(levelname)s:%(message)s',datefmt='%d/%m/%Y %I:%M:%S')
                logging.warning("Log file not found so it created temporary log file to capture the script logs"+Logfile)
        try:
                if os.path.isfile(hc_filename):
                        print(hc_filename)
                        hc_File = open(hc_filename, 'r+')
                        hc_File.truncate(0)
                        logging.info('Cleaning the content of health check result file {}'.format(hc_filename))
                else:
                        hc_File =  open(hc_filename, 'a+')
                        logging.info('Health check result file has been created with --{}'.format(hc_filename))
        except:
                        e = sys.exc_info()[1]
                        logging.debug("Failed with ErrorException -- " + str(e))
                        sys.exit()


        '''
                This function will create the textfile
                whose content will be used as a emailbody.
        '''
        def generate_healtcheck_emailbody(check_id,result_tag,comments,hostname_list):
                print("generate_healtcheck_emailbody called")
                if data["Mail"]["Secure_Mode"]["Enable"]:
                        if hostname_list:
                                hostlist = hostname_list.count(",") + 1
                        else:
                                hostlist = ""
                        print("=> Secure Mode")
                        if data["Mail"]["Consolidation_Counter"] and data["Mail"]["Consolidation_Counter"] != 'NA':
                                hc_File.write(data["Mail"]["Secure_Mode"]["Classification_Text"]+'Check Result:{}~~~{}~~~{}:{}~~~{}\n'.format(check_id,result_tag,comments,hostlist,utc_time))
                        else:
                                hc_File.write(data["Mail"]["Secure_Mode"]["Classification_Text"]+'Check Result:{}~~~{}~~~{}:{}~~~{}\n'.format(check_id,result_tag,comments,hostlist,utc_time))
                elif data["Mail"]["Test_Mode"]:
                        print("=> Test Mode")
                        if data["Mail"]["Consolidation_Counter"] and data["Mail"]["Consolidation_Counter"] != 'NA':
                                hc_File.write('[TEST]Check Result:{}~~~{}~~~{}:{}~~~{}\n'.format(check_id,result_tag,comments,hostname_list,utc_time))
                        else:
                                hc_File.write('[TEST]Check Result:{}~~~{}~~~{}:{}~~~{}\n'.format(check_id,result_tag,comments,hostname_list,utc_time))
                else:
                        print("=> Normal Mode")
                        if data["Mail"]["Consolidation_Counter"] and data["Mail"]["Consolidation_Counter"] != 'NA':
                                hc_File.write('Check Result:{}~~~{}~~~{}:{}~~~{}\n'.format(check_id,result_tag,comments,hostname_list,utc_time))
                        else:
                                hc_File.write('Check Result:{}~~~{}~~~{}:{}~~~{}\n'.format(check_id,result_tag,comments,hostname_list,utc_time))


        excluded_resources = []
        for health_check in data['DORM_Health_Checks']:
                check_id = str(health_check['Check_Id'])
                for sub_check in health_check['Sub_Checks']:
                        file_name = str(sub_check['Name'])
                        if sub_check['Exclusion_List'] != None:
                                excluded_resources.extend(sub_check['Exclusion_List'].split(','))

                        try:
                                output_uri = key+'aws_health_check_processed_output/'+ file_name+".csv"
                                s3_object = s3.Object(bucket_name,  output_uri)
                                raw_data = s3_object.get()['Body'].read().decode('utf-8').splitlines()
                                print(output_uri)
                        except:
                                Exception=PrintException()
                                print(Exception)
                                put_data(f"S3 bucket :{bucket_name} ", "Reading csv file from S3 bucket", "Unable to read csv file", Exception)
                                print("File Not Found")
                                print("File Name: "+ output_uri)
                                continue
                        
                        else:     
                                failed_ids = []
                                flag = 'Pass'
                                rows = csv.reader(raw_data)
                                header = next(rows)
                                if 'Resource Id' in header:
                                    Id= header.index('Resource Id')
                                index= header.index('Result')
                                #print(index)
                                for row in rows:
                                        
                                        if (str(row[index]) =='FAIL' or str(row[index]) == 'Fail'):
                                                failed_ids.append(row[Id])
                                                flag = 'Fail'
                                
                                
                                failhostslist = sorted(set(failed_ids))
                                failedhosts = ','.join(failhostslist)
                                if flag == "Fail":
                                        generate_healtcheck_emailbody(check_id,'Fail',file_name + "~~~ failed on following servers/device(s)",failedhosts)
                                else:
                                        generate_healtcheck_emailbody(check_id,'Pass',file_name + "~~~ check on all servers/devices is healthy","")

        
        excluded_resources = list(set(excluded_resources))
        general_details = "\nHost Server: "+ "#####" +"\nServers\Devices Checked: "+ "#####" +"\nServers\Devices Excluded: "+ str(excluded_resources) +"\nPackage Name: "+ "#####" +"\nScript Version: " + str(data['Version']) + "\nConfig Version: " + str(data['Version'])
        hc_File.write(general_details)
        hc_File.close()
        upload_status_report(hc_filename, bucket_name,  key+ "aws_health_check_result/" + result_file_name)



'''
    This function takes file uri, fields and rows that needs 
    to be added and then creates the CSV file for it.
'''
def upload_status_report(file_uri, bucket_name, key):
    print("upload_status_report called")
    try:
        s3 = boto3.resource('s3', config=config)
        s3.meta.client.upload_file(file_uri, bucket_name, key)
    except:
        Exception=PrintException()
        print(Exception)
        put_data("S3 Bucket", "Upload file uri to S3 bucket","Error Occured during File Upload", Exception)
        print("Bucket Name: ", bucket_name)
        print("Key :", key)
    else:
        print("Successfully Uploaded")

def token(event, task_token):
    sf = boto3.client('stepfunctions')
    sf_output = json.dumps(event)
    sf_response = sf.send_task_success(
        taskToken=task_token,
        output=str(sf_output)
    )
    return sf_response


def lambda_handler(event, context):
    # TODO implement
    print("Received Event: ", event)
    global uniqueID
    try:
        task_token = event['token']
        event = event["Payload"]
        uniqueID = event["uniqueID"]
        hc_put_key(os.environ['AWS_LAMBDA_FUNCTION_NAME'])
        S3_directory_name = event["S3_directory_name"]+ "aws_service_health_check/"
        health_check_result(event['S3_Bucket'], S3_directory_name)
    except:
        Exception=PrintException()
        print(Exception)
        print("Error Occured")
        put_data(f"{os.environ['AWS_LAMBDA_FUNCTION_NAME']} script", "", "Error Occured", Exception)

    #return event
    return token(event, task_token)

if __name__ == "__main__":
    event1 = {"S3_Bucket":"bucket-for-testing-221", "S3_directory_name":"feature_aws_health_checks/"}   
    lambda_handler(event1, "")