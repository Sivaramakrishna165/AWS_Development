'''
This Lambda script deletes the cloud watch rules which are releated to the particular month as part of post patching activity.
'''

import boto3
import sys
import os
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))

client = boto3.client('events',config=config)
standard_snow_status = os.environ['standard_snow_status']
adhoc_snow_status= os.environ['adhoc_snow_status']

lambda_client = boto3.client('lambda',config=config)
LF_ID_pw_status_check = os.environ['PatchingWindow_status_check'] #'dxcms-pa-lam-check-pw-status'
LF_ID_Snow_status_check = os.environ['Service_now_status_check']


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
        snow_status = ssmParameter['Parameter']['Value']
        return snow_status
    except:
        print(PrintException())


def fetch_targets_by_rule(CloudwatchRules):
    try:

        CloudwatchTargets = []
        for i in range(len(CloudwatchRules)):
            print("CloudwatchRules : ",CloudwatchRules[i])
            response = client.list_targets_by_rule(
                Rule = CloudwatchRules[i]
            )
            y = (response['Targets'])
            print("y ",y)
            res = [ sub['Id'] for sub in y]
            CloudwatchTargets.append(res)
        print("CloudwatchRules : ",CloudwatchRules)
        print("CloudwatchTargets : ",CloudwatchTargets)
        res_dic = {CloudwatchRules[i]: CloudwatchTargets[i] for i in range(len(CloudwatchRules))}
        print("res_dic : ",res_dic)
        return res_dic
    except:
        err = PrintException()


def lambda_handler(event,context):
    global TagValues,region
    region = event['region']
    S3_directory_name = event['S3_directory_name']
    month = S3_directory_name.split("/")[0]
    Snow_CW_rule = 'SNOW_CR_Status_Check_' + month
    TagValues = event['PatchInstallOn']
    Patching_Type= event['Patching_Type']
    CWrules = ["Install_Patch_" + TagValues + "_" + region, "PatchScan_" + TagValues + "_" + region , "Peform_PreTask_" + TagValues + "_" + region]
    if Patching_Type == 'Adhoc':
        snow_enable_status = read_ssm_parameter(adhoc_snow_status)
        #CWrules.append("DXCAdhocSchedulePatching_" + region)
    else:
        snow_enable_status = read_ssm_parameter(standard_snow_status)

    if snow_enable_status == "ON":
        CWrules.append("SNOW_CR_Status_Check_" + TagValues)
    else:
        if Patching_Type == 'Standard':
            CWrules.append("Patching_Window_Check_" + TagValues)
    print("Cloud Watch Rules : ", CWrules)
    if CWrules == None or CWrules == "" or CWrules == []:
        print(f"no Cloud Watch rules found with tag value : {TagValues} . Hence, skipping execution...")
    else:
        Targets = fetch_targets_by_rule(CWrules)
        print("Targets : ",Targets)
        for key,value in Targets.items():
            print("in remove target loop : ",key," ",value)
            response = client.remove_targets(
                Rule = key,
                Ids = value
            )
        for i in range(len(CWrules)):
            print("in delete CW rule loop : ",CWrules[i])
            response = client.delete_rule(
                Name = CWrules[i]
            )
            
        #Remove trigger permissions from lambda
        statement_dict = {}
        statement_dict[LF_ID_pw_status_check] = 'PatchingWindowCheck_'+TagValues
        statement_dict[LF_ID_Snow_status_check] = 'Patching_'+TagValues
        
        for skey,svalue in statement_dict.items():
            print("Trying to remove permission:",svalue, "from Lambda:", skey)
            try:
                response = lambda_client.remove_permission(
                            FunctionName=skey,
                            StatementId=svalue)
                print("Lambda Permission removed for ",svalue)
            except:
                print("No Permission found: ", svalue)
		
    return event

if __name__ == "__main__":

    event1 = {
	"PatchInstallOn": "testing-MAY_4_2023_13_5_4HRS",
	"S3_Bucket": "dxcms.patchingautomation.567529657087.us-west-1",
	"S3_directory_name": "MAY_2023/us-west-1/patchJobId_4470e752-fe00-11ed-a9be-cbfddefb16be",
	"S3_Folder_Name": "patching_reports",
	"region": "us-west-1"
    }
    
    lambda_handler(event1, "") 
