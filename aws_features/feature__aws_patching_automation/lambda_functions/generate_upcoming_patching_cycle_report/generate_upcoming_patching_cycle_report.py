'''
This Lambda script is used to 
- Fetch Account details 
- get CloudWatch rules info from customer account for Patching cycles 
- generate an upcoming patch cycles report and writes it to the Customer bucket
- push the report to a centralized bucket for PBI Integration
'''

# Importing needed libraries
import sys
import datetime
import os
import csv
import boto3
from datetime import datetime
from botocore.config import Config

#Declaring global variables
config=Config(retries=dict(max_attempts=10, mode='standard'))
s3 = boto3.resource('s3', config=config)

current_time = datetime.now()
month = current_time.strftime("%b").upper()+"_"+current_time.strftime("%Y")

region = os.environ['AWS_REGION']
destination_bucket = os.environ['destination_bucket_name']
customer = os.environ['customer_name']
#destination_bucket_name = "cloudops-patching-compliance-reports"
#destination_key = ""

#Captures and Prints Error/Exceptions
def PrintException():
    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    captureErr = "Line No. : " + str(lineno)  + " | ERROR: " + str(exc_obj)
    return captureErr

#Read SSM parameter for destination bucket and customer name
def read_ssm_parameter(ssm_parameter):
    try:
        ssm_client = boto3.client('ssm',config=config)
        ssmParameter = ssm_client.get_parameter(Name=ssm_parameter)
        ssm_parameter_value = ssmParameter['Parameter']['Value']
        
    except:
        print(PrintException())
    return ssm_parameter_value


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


#Get CloudWatch rules details for upcoming patch schedule
def get_cloudwatchevent_details():
    try:
        event_client = boto3.client('events',config=config)
        response = event_client.list_rules(NamePrefix='Install_Patch_')
        rules_details = response['Rules']
        #print("Listing all rules : ", rules_details)
        CloudWatchRules = [[rule['Name'],rule['ScheduleExpression'],rule['State']] for rule in rules_details ]
        print(CloudWatchRules)
        rules_list = []
        
        for rule in CloudWatchRules:
            rname = rule[0]
            rpatch_group = rule[0].split('-')[0].split('_')[-1]
            rschedule = rule[1].replace('cron(','').replace(')','').split(' ')
            rstatus = rule[2]
            rmins,rhours,rday,rmonth,ryear = rschedule[0], rschedule[1],rschedule[2],rschedule[3],rschedule[5]
            if int(rmins)<10:
                rtime = rhours+':0'+rmins
            else:
                rtime = rhours+':'+rmins
            
            #Check if the schedule is upcoming
            utc_time = datetime.utcnow()
            schedule_str = rmonth+' '+rday+' '+ryear+' '+rhours+':'+rmins
            schedule_datetime = datetime.strptime(schedule_str, '%b %d %Y %H:%M')
            if utc_time < schedule_datetime:
                rules_list.append((rname,rstatus,rpatch_group,rtime,rday+'-'+rmonth+'-'+ryear))
    except:
        print(PrintException())
    return rules_list
    
# Create a CSV file
def write_csv_file(rules_list):
    try:
        account_details = (account_Id,account_name,customer_name,region)
        with open(local_output_file_path, 'w', newline='') as csvfile:
            filewriter = csv.writer(csvfile, delimiter=',')  
            filewriter.writerow(['Account ID','Account name','Customer name','Region','Rule Name','Rule Status','Patch Group','Time(UTC)','Date'])
            for rule in rules_list:
                filewriter.writerow(account_details+rule)
    except:
        print(PrintException())
        
#upload csv file to customer s3 bucket
def upload_file_into_s3(bucket_name,output_local_file_path,output_s3_key_file_path):
    try:
        s3_resource = boto3.resource('s3', config=Config(signature_version='s3v4'))
        bucket = s3_resource.Bucket(bucket_name)
        print("Key : ", output_s3_key_file_path)
        print("fileFullName_Local : ",output_local_file_path)
        bucket.upload_file(output_local_file_path, output_s3_key_file_path)
    except:
        print(PrintException())


# Copy objects from one bucket to another
def copy_s3_object(bucket_name, source_key, destination_path):
    try:
        s3_resource = boto3.resource('s3')
        #To copy reports in 'UpcomingPatchingCycle' folder at Destination bucket
        destination_path = destination_path+'UpcomingPatchingCycle/'
        
        #destination_bucket_name = 'dxcms-patchingautomation-test' 
        print("Copying ", source_key)
        copy_source = {'Bucket': bucket_name,
                        'Key': source_key }
        target_key = str(source_key).split("/")[-1]
        print(destination_bucket_name+'/'+destination_path+target_key)
        s3_resource.Bucket(destination_bucket_name).Object(destination_path+target_key).copy(copy_source, ExtraArgs={'ACL': 'bucket-owner-full-control'})
    except:
        print(PrintException())
    return destination_path+target_key


def lambda_handler(event, context):

    try:
        # Getting Current Date and time
        print("Current Time is :", current_time)
        print("Current Month is :", month)
        
        global account_Id, account_name, customer_name, customer_bucket_name, destination_bucket_name, destination_key, local_output_file_path
        
        #Getting Account Info
        account_Id, account_name = get_aws_account_info()
        print("Account ID is :", account_Id)
        print("Account Name is :", account_name)
        print("Region is :", region)
        
        #Getting Customer Bucket details
        customer_bucket_name = "dxcms.patchingautomation."+account_Id+"."+region
        s3_path = "patching_reports/"
        print("Bucket Name is :", customer_bucket_name)
        print("Reports path is :", s3_path)
        
        #Destination Bucket details
        report_destination = str(read_ssm_parameter(destination_bucket)).split("/")
        print(report_destination)
        destination_bucket_name = report_destination[0]
        destination_key = '/'.join(report_destination[1:])
        print("Destination Bucket : ", destination_bucket_name )
        print("Destination Key : ", destination_key)
        customer_name = read_ssm_parameter(customer)
        print("Customer Name :", customer_name)
        
        file_key = "upcoming_patching_"+account_Id+"_"+region+".csv"
        local_output_file_path = "/tmp/" + file_key
        
        #Get EventBridge rules details
        upcoming_patch_cycles = get_cloudwatchevent_details()
        write_csv_file(upcoming_patch_cycles)
        upload_file_into_s3(customer_bucket_name,local_output_file_path,s3_path+file_key)
        destination_path = copy_s3_object(customer_bucket_name, s3_path+file_key, destination_key)
        
    except:
        print(PrintException())
    return {
        'Region': region,
        'Account_id': account_Id,
        'Account_name' : account_name,
        'Customer_name' : customer_name,
        'Upcoming_Patch_cycles': len(upcoming_patch_cycles),
        'Source_Reports_Path' : customer_bucket_name+'/'+s3_path,
        'Report_Name' : file_key,
        'Destination_report_path' : destination_bucket_name+'/'+destination_path
    }
# sample test case
if __name__ == "__main__":
    
    event1 = {}
    lambda_handler(event1, "")
