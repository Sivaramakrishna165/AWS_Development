'''
This Lambda script is used to 
- Fetch Account ID and name
- get EC2 instances info from customer account
- get Baseline details from Patch Manager
- get path of the reports in customer bucket
- perform a patch scan of the instances
- get post patch scan reports in the customer bucket
- generate a consolidated report - merges the data and writes it to the Customer bucket
- push the report to a centralized bucket for PBI Integration
'''

# Importing needed libraries
import time
import datetime
import sys
import pandas as pd
import os
import json
import io
import csv
import boto3
from io import StringIO
from datetime import datetime
from botocore.config import Config
from botocore.errorfactory import ClientError


#Declaring global variables
config=Config(retries=dict(max_attempts=10, mode='standard'))
s3 = boto3.resource('s3', config=config)

current_time = datetime.now()
month = current_time.strftime("%b").upper()+"_"+current_time.strftime("%Y")

region = os.environ['AWS_REGION']
destination_bucket = os.environ['destination_bucket_name']

#destination_bucket_name = "cloudops-patching-compliance-reports"
#destination_key = ""


#Captures and Prints Error/Exceptions
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
        ssm_parameter_value = ssmParameter['Parameter']['Value']
        return ssm_parameter_value
    except:
        print(PrintException())
        
#Check if the S3 path exists
def path_exists(bucket_name, path):
    try:
        s3.ObjectSummary(bucket_name=bucket_name, key=path).load()
    except ClientError as e:
        if e.response['Error']['Code'] == "404":
            return False
        else:
            raise e
    return True


#Fetch Account Info(Customer)
def get_aws_account_info():
    try:
        sts = boto3.client("sts",config=config)
        accountId = sts.get_caller_identity()["Account"]  
        # fetch Account_Name for the Account_Id      
        accountName = boto3.client('iam',config=config).list_account_aliases()['AccountAliases'][0]
    except:
        print(PrintException())
    return accountId, accountName
    

def get_osname_instance(instance_id, inst_platform):
    ssm_client = boto3.client('ssm',region_name = region,config=config)
    #ssm_client = session.client('ssm',region_name=region)

    if inst_platform == "Linux":
        try:
            cmd = 'cat /etc/os-release | head -n 1 | sed "s/NAME=//"'
            response = ssm_client.send_command(InstanceIds=[instance_id],DocumentName="AWS-RunShellScript",Parameters={'commands': [cmd]},)
            time.sleep(8)
            command_id = response['Command']['CommandId']
            output = ssm_client.get_command_invocation(CommandId=command_id,InstanceId=instance_id,)
            command_status = output['Status']

            if command_status == 'Success':
                r = json.dumps(output)
                loaded_r = json.loads(r)
                os_details = loaded_r['StandardOutputContent']

                cmd_op = os_details.strip('\r').strip('\n').strip('"')
                return cmd_op

            else:
                cmd_op = ''
                return cmd_op
        except:
            error = PrintException()
            print("ERROR : Unable to Check OS - ", error)
            return "Unable to Check OS"

    elif inst_platform == "Windows":
        try:
            cmd = '(gwmi win32_operatingsystem).caption'
            response = ssm_client.send_command(InstanceIds=[instance_id],DocumentName="AWS-RunPowerShellScript",Parameters={'commands': [cmd]},)            
            time.sleep(8)
            command_id = response['Command']['CommandId']
            output = ssm_client.get_command_invocation(CommandId=command_id,InstanceId=instance_id,)
            command_status = output['Status']

            if command_status == 'Success':
                r = json.dumps(output)
                loaded_r = json.loads(r)
                os_details = loaded_r['StandardOutputContent']

                cmd_op = os_details.strip("\n").rstrip("\r")
                return cmd_op

            else:
                cmd_op = ''
                return cmd_op
        except:
            error = PrintException()
            print("ERROR : Unable to Check OS - ", error)
            return "Unable to Check OS"
    else:
        return "Instance Platform Unknown"

# Generate Compliance status of the instances
def list_compliance_report(instanceId,platform,non_compliant_next_token,Compliance_status,Critical_noncompliant,Security_noncompliant,Other_noncompliant,Baseline_id):
    try:
        ssm_client = boto3.client('ssm',region_name = region,config=config)

        if platform == "Windows":
            security_classification = "SecurityUpdates"
            critical_classification = "CriticalUpdates"
        else:
            security_classification = "Security"
            critical_classification = "Critical"

        Critical_noncompliant_count = 0
        Security_noncompliant_count = 0
        Other_noncompliant_count = 0
        
        
        if non_compliant_next_token == '' or non_compliant_next_token == None:   
            #print("Non Compliant token is NONE")
            Critical_NonCompliant_Patch_Id = ''
            Security_NonCompliant_Patch_Id = ''
            Other_NonCompliant_Patch_Id = ''

            non_compliant_response = ssm_client.list_compliance_items(Filters=[{'Key': 'Status','Values': ['NON_COMPLIANT',],},],
                                                                      ResourceIds=[instanceId,],MaxResults = 50)
            try:
                non_compliant_next_token = non_compliant_response['NextToken']
                #print("non_compliant_next_token : ",non_compliant_next_token)
            except:
                non_compliant_next_token == None
        else:
            #print("Non Compliant token is NOT NONE")
            non_compliant_response = ssm_client.list_compliance_items(Filters=[{'Key': 'Status','Values': ['NON_COMPLIANT',],},],
                                                                      ResourceIds=[instanceId,],
                                                                      NextToken = non_compliant_next_token,
                                                                      MaxResults = 50)
            try:
                non_compliant_next_token = non_compliant_response['NextToken']
            except:
                non_compliant_next_token = None

        #print("non_compliant_next_token : ",non_compliant_next_token)
        

        if non_compliant_response['ComplianceItems'] == []:
            #Compliance_status.append('Compliant')
            compliant_response = ssm_client.list_compliance_items(Filters=[{'Key': 'Status','Values': ['COMPLIANT',],},],
                                                                  ResourceIds=[instanceId,],MaxResults = 50)
            if compliant_response['ComplianceItems'] == []:
                Compliance_status.append('NA')
            else :
                Compliance_status.append('Compliant')


            for item in compliant_response['ComplianceItems']:       
                if Baseline_id == "NA":
                    try:
                        Baseline_id = item['Details']['PatchBaselineId']
                    except:
                        print("")

        else:

            
            critical_noncompliant_patch_id_string = ''
            security_noncompliant_patch_id_string = ''
            other_noncompliant_patch_id_string = ''
            for item in non_compliant_response['ComplianceItems']:       
                try:
                    if item['Details']['Classification'] == critical_classification:
                        patch_id = item["Id"]
                        try:
                            CVE_id = item['Details']['CVEIds']
                        except:
                            CVE_id = ""
                        if CVE_id != "":
                            patch_id = str(patch_id) + " ( "+ str( CVE_id ) + ")"
                        else:
                            patch_id = str(patch_id)
                        Critical_noncompliant.append(str(patch_id))
                        Compliance_status.append('Non_Compliant')
                    if item['Details']['Classification'] == security_classification:
                        patch_id = item["Id"]
                        try:
                            CVE_id = item['Details']['CVEIds']
                        except:
                            CVE_id = ""
                        if CVE_id != "":
                            patch_id = str(patch_id) + " ( "+ str( CVE_id ) + ")"
                        else:
                            patch_id = str(patch_id)
                        Security_noncompliant.append(str(patch_id))
                        Compliance_status.append('Non_Compliant')
                    if item['Details']['Classification'] != security_classification and item['Details']['Classification'] != critical_classification:
                        patch_id = item["Id"]
                        try:
                            CVE_id = item['Details']['CVEIds']
                        except:
                            CVE_id = ""
                        if CVE_id != "":
                            patch_id = str(patch_id) + " ( "+ str( CVE_id ) + ")"
                        else:
                            patch_id = str(patch_id)
                        Other_noncompliant.append(str(patch_id))
                        Compliance_status.append('Non_Compliant')
                except:
                    print("there is no classification and PatchState")# item['Details']['PatchState'])
                    Compliance_status.append('NA')

                if Baseline_id == "NA":
                    try:
                        Baseline_id = item['Details']['PatchBaselineId']
                    except:
                        print("")

            Critical_noncompliant_count = len(Critical_noncompliant)
            print("Critical Patch count : ",Critical_noncompliant_count)

            Security_noncompliant_count = len(Security_noncompliant)
            print("Security Patch count : ",Security_noncompliant_count)

            Other_noncompliant_count = len(Other_noncompliant)
            print("Other_noncompliant Patch count : ",Other_noncompliant_count)

            if len(Critical_noncompliant) > 1 :
                Critical_NonCompliant_Patch_Id = critical_noncompliant_patch_id_string.join([str((elem)+",") for elem in Critical_noncompliant])
            if len(Critical_noncompliant) == 0 :
                Critical_NonCompliant_Patch_Id = ''
            if len(Critical_noncompliant) == 1 :
                Critical_NonCompliant_Patch_Id = Critical_noncompliant[0]
            if len(Security_noncompliant) > 1 :
                Security_NonCompliant_Patch_Id = security_noncompliant_patch_id_string.join([str((elem)+",") for elem in Security_noncompliant ])
            if len(Security_noncompliant) == 0 :
                Security_NonCompliant_Patch_Id = ''
            if len(Security_noncompliant) == 1 :
                Security_NonCompliant_Patch_Id = Security_noncompliant[0]
            if len(Other_noncompliant) > 1 :
                Other_NonCompliant_Patch_Id = other_noncompliant_patch_id_string.join([str((elem)+",") for elem in Other_noncompliant ])
            if len(Other_noncompliant) == 0 :
                Other_NonCompliant_Patch_Id = ''
            if len(Other_noncompliant) == 1 :
                Other_NonCompliant_Patch_Id = Other_noncompliant[0]
        
        if non_compliant_next_token == '' or non_compliant_next_token == None:
            if 'Non_Compliant' in Compliance_status:
                Compliance_status_str = "Non Compliant"
            if 'NA' in Compliance_status:
                Compliance_status_str = "NA"
            if 'Compliant' in Compliance_status:
                Compliance_status_str = "Compliant"

        else:
            instanceId,platform,Compliance_status_str,Critical_noncompliant_count,Security_noncompliant_count,Other_noncompliant_count,Critical_NonCompliant_Patch_Id,Security_NonCompliant_Patch_Id,Other_NonCompliant_Patch_Id,Baseline_id = list_compliance_report(instanceId,platform,non_compliant_next_token,Compliance_status,Critical_noncompliant,Security_noncompliant,Other_noncompliant,Baseline_id)
        
        return instanceId,platform,Compliance_status_str,Critical_noncompliant_count,Security_noncompliant_count,Other_noncompliant_count,Critical_NonCompliant_Patch_Id,Security_NonCompliant_Patch_Id,Other_NonCompliant_Patch_Id,Baseline_id
    except:
        print(PrintException())    
        

#Gets List of EC2 Instances-Id, Type, Status, Platform, OS Name, Tags in the Account and their respective Patch Compliance details
def get_instances_info():
    try:
        instances_df = pd.DataFrame(columns=['Instance ID', 'Instance name', #'Instance Type', 
                                                'State', 'Patch Group', 'Downtime Window', 'Apply Patching', 'DXC Managed', 
                                                'Platform Type', 'Operation System'])
        ec2 = boto3.client('ec2',config=config)
        ec2_list = ec2.describe_instances()
        
        for ec2 in ec2_list['Reservations']:
            for instance in ec2["Instances"]:
                tags = {}
                platform = ""
                print(instance['InstanceId'], instance["InstanceType"], instance["State"]["Name"])
                instance_id = instance['InstanceId']
                
                #Get Instance Platform
                try:
                    if instance['Platform'] == 'windows':
                        platform = "Windows"
                except:
                    platform = "Linux"
                
                
                #Get Tag values
                tag_tuple = ('Name', 'Patch Group', 'Downtime Window', 'ApplyPatching', 'DXCProduct', 'OSName')
                for tag in instance["Tags"]:
                    if tag["Key"] in tag_tuple:
                        tags.update({tag["Key"] : tag["Value"]})
                for missing_tag in tag_tuple-tags.keys():
                    tags.update({missing_tag : ""})
                if tags['DXCProduct'] == "" :
                    tags['DXCProduct'] = 'No'
                print("Tags dict : ", tags)
                
                #Get Operating System name
                if tags['OSName'] != "":
                    os_name = tags['OSName']
                else:
                    os_name = get_osname_instance(instance_id, platform)
                
                #Get compliance Info for the instance
                compliance_details = list(list_compliance_report(instance_id,platform,None,[],[],[],[],'NA'))
                print(compliance_details)
                
                #Add all instance details to the dataframe as a row
                instances_df = pd.concat([instances_df, pd.DataFrame([{'Instance ID': instance["InstanceId"], 
                                'Instance name' : tags['Name'],
                                #'Instance Type' : instance["InstanceType"], 
                                'State' : instance["State"]["Name"], 
                                'Patch Group' : tags['Patch Group'],
                                'Downtime Window' : tags['Downtime Window'],
                                'Apply Patching' : tags['ApplyPatching'],
                                'DXC Managed' : tags['DXCProduct'],
                                'Platform Type' : platform,
                                'Operation System': os_name,
                                'Compliance status' : compliance_details[2],
                                'Critical noncompliant count' : compliance_details[3],
                                'Security noncompliant count' : compliance_details[4],
                                'Other noncompliant count' : compliance_details[5],
                                'Critical NonCompliant Patch_Id(KB)' : compliance_details[6],
                                'Security NonCompliant Patch_Id(KB)' : compliance_details[7],
                                'Other NonCompliant Patch_Id(KB)' : compliance_details[8],
                                'Baseline ID Used' : compliance_details[9]    
                                }])], ignore_index = True)
        print(instances_df)
    except:
        print(PrintException())
    return instances_df


# Gets Baseline details from Patch Manager
def get_patch_baselines_info(baselines_list):
    baselines_list_info = {}
    try:
        ssm_client = boto3.client('ssm', config=config)
        response = ssm_client.describe_patch_baselines()
        for baseline in response["BaselineIdentities"]:
            if baseline['BaselineId'].split("/")[-1] in baselines_list:
                #print(baseline['BaselineId'].split("/")[-1],":", baseline["BaselineName"])
                baselines_list_info.update({baseline['BaselineId'].split("/")[-1] : baseline["BaselineName"]})
    except:
        print(PrintException())
    
    return baselines_list_info 


# Get Full path details of the reports from Customer Bucket
def get_full_path(bucket_name, path, run_type):
    full_reports_path = []
    #Path at which the patch compliance report will be stored
    compliance_report_path = ""
    try:
        my_bucket = s3.Bucket(bucket_name)
        
        #Check run_type to get the correct reports
        if run_type == 'Scheduled':
            pattern = "/ServersList/PatchScanReport_"
        elif run_type == 'PostPatching':
            pattern = "/PatchScanReports/Post/Post_PatchScanReport"

        #Check for the reports and get the full path    
        if path_exists(bucket_name, path+'/'):
            for my_bucket_object in my_bucket.objects.filter(Prefix=path):
                my_key = my_bucket_object.key
                if "patchJobId_" in my_key:
                    if pattern in my_key:
                        print(my_key)
                        full_reports_path.append(my_key)
                        
        compliance_report_path = path+"/PatchComplianceReports/"                
    except:
        print(PrintException())
    return full_reports_path, compliance_report_path


#Reads report into a dataframe 
def get_patch_scan_report(bucket_name, reports_key):
    try:
    
        s3_client = boto3.client('s3',config=config)
        patch_scan_df = pd.DataFrame()
        for report_key in reports_key:
            csv_obj = s3_client.get_object(Bucket=bucket_name, Key=report_key)
            body = csv_obj['Body']
            csv_string = body.read().decode('utf-8')
            #print("Reading Post Patch Scan report :\n",csv_string,"\n")
            report_df = pd.read_csv(StringIO(csv_string))
            #print("Printing df from Post Patch Scan report",report_df)
            patch_scan_df = pd.concat([patch_scan_df, report_df], ignore_index = True)
            
        print(patch_scan_df)
    except:
        print(PrintException())   
    return patch_scan_df
    
# Merge both reports to generate a final report
def merge_reports_info(report_df1, report_df2, run_type, account_Id, account_name):
    try:
        merged_df = pd.DataFrame()
        if run_type == 'PostPatching':
            merged_df = pd.merge(report_df1, report_df2, on = ['Instance ID','Instance name'], how = 'inner')
        else:
            merged_df = report_df1
        
        merged_df['Date & Time(UTC)'] = datetime.today().strftime('%Y-%m-%d %H:%M')
        merged_df.insert(loc = 0, column = 'Account ID', value = account_Id)
        merged_df.insert(loc = 1, column = 'Account_Name', value = account_name)
        

    except:
        print(PrintException())
    return merged_df


  
# Create a CSV file and store in the desired S3 path
def write_df_to_csv(instances_info_df, customer_bucket_name, bucket_key, account_Id, account_name, region_name, run_type):
    try:       
        report_name = run_type+'_PatchComplianceReport_'+account_Id+'_'+region_name+'_'+month+'.csv'
        print("Report Name:",report_name)
        patch_report_path = bucket_key+report_name
        final_s3_path = 's3://'+customer_bucket_name+'/'+patch_report_path
        print("Writing Data to Path:", final_s3_path)
        #wr.s3.to_csv(df=instances_info_df, path=final_s3_path, index=False)
        os.chdir('/tmp')
        print(os.getcwd())
        save_path = os.path.join(os.getcwd(),report_name)
        print("No. of rows in df:",len(instances_info_df))
        instances_info_df.to_csv(save_path, index=False)
        print(os.listdir())
        s3.meta.client.upload_file(save_path, customer_bucket_name,patch_report_path)
    except:
        print(PrintException())
    return patch_report_path
        

# Copy objects from one bucket to another
def copy_s3_object(bucket_name, source_key, destination_path, run_type):
    try:
        s3_resource = boto3.resource('s3',config=config)
        #To copy reports in Pre and Post folders at Destination bucket
        if run_type == 'PostPatching':
            destination_path = destination_path+'Post/'
        elif run_type == 'Scheduled':
            destination_path = destination_path+'Pre/'
        
        print("Copying ", source_key)
        copy_source = {'Bucket': bucket_name,
                        'Key': source_key }
        target_key = str(source_key).split("/")[-1]
        print(destination_bucket_name, destination_path+target_key)
        s3_resource.Bucket(destination_bucket_name).Object(destination_path+target_key).copy(copy_source, ExtraArgs={'ACL': 'bucket-owner-full-control'})
        #s3.meta.client.copy(copy_source, destination_bucket_name, destination_path+target_key)

    except:
        print(PrintException())
    return destination_path+target_key


#-----------------------------------------------------------------------------------------------
def lambda_handler(event, context):
    # run_type can be 'Scheduled' or 'PostPatching'
    run_type = event["Run_type"]
    
    try:
        # Getting Current Date and time
        print("Current Time is :", current_time)
        print("Current Month is :", month)
        
        global account_Id, account_name, customer_bucket_name, destination_bucket_name, destination_key
        
        #Getting Account Info
        account_Id, account_name = get_aws_account_info()
        print("Account ID is :", account_Id)
        print("Account Name is :", account_name)
        print("Region is :", region)
        
        #Getting EC2 Instances Info in Customer Account
        instances_info_df = get_instances_info()
        
        #Getting Customer Bucket details
        customer_bucket_name = "dxcms.patchingautomation."+account_Id+"."+region
        path = "patching_reports/PATCHING/"+month+"/"+region
        print("Bucket Name is :", customer_bucket_name)
        print("Reports path is :", path)
        
        #Getting full reports path from customer bucket
        full_reports_path, compliance_report_path = get_full_path(customer_bucket_name,path, run_type)
        
        #Getting report data
        patch_scan_df = get_patch_scan_report(customer_bucket_name, full_reports_path)
        patch_scan_df = patch_scan_df[['Instance ID','Instance name']]
        
        #Getting Baselines Data
        baselines_list = list(instances_info_df["Baseline ID Used"])
        baselines_list_info = get_patch_baselines_info(baselines_list)
        print("Baselines :", baselines_list_info)
        
        
        #Adding Baselines Info to the report data
        instances_info_df["Baseline Name"] = instances_info_df["Baseline ID Used"].replace(baselines_list_info)
        
        final_merged_df =  merge_reports_info(instances_info_df, patch_scan_df, run_type, account_Id, account_name)
        source_report_key = write_df_to_csv(final_merged_df, customer_bucket_name, compliance_report_path, account_Id, account_name, region, run_type)
        
        
        #Destination Bucket details
        report_destination = str(read_ssm_parameter(destination_bucket)).split("/")
        print(report_destination)
        destination_bucket_name = report_destination[0]
        destination_key = '/'.join(report_destination[1:])
        print("Destination Bucket : ", destination_bucket_name )
        print("Destination Key : ", destination_key)
        
        #Copy Report to Destination S3 Bucket
        #write_df_to_csv(instances_info_df, destination_bucket_name, destination_key, account_Id, account_name, region)
        destination_path = copy_s3_object(customer_bucket_name, source_report_key, destination_key, run_type)
        
    
    except:
        print(PrintException())
    return {
        'Run_type' : run_type,
        'Region': region,
        'Account_id': account_Id,
        'Source_Reports_Path' : 's3://'+customer_bucket_name+'/'+path+'/',
        'Full_Path' : full_reports_path,
        'Compliance_report_Path' : compliance_report_path,
        'Destination_path' : destination_bucket_name+'/'+destination_path
        
    }

# sample test case
if __name__ == "__main__":
    # run_type can be 'Scheduled' or 'PostPatching'
    event1 = {  "Run_type": "Scheduled"}
    lambda_handler(event1, "")
