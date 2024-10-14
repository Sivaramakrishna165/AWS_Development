'''
 The FeatureCreateHardened AMIs will help in creating the CoreCM Hardened AMI automatically
 The AMIs information will be saved in the DynamoDB table
 For initating create Hardened amis -{"RequestType": "CreateHardenedAmis"}
 For viewing the status {"RequestType": "ViewCreateHardenedAmisStatus"}
'''

import json, os
from boto_helper import boto_helper
from datetime import datetime

boto_helper_obj = boto_helper()
create_cust_ami_key_pair = 'dxc-awsms-FeatureCreateHardenedAmis'
view_hardened_amis_rule = 'AWSMS-ViewCreateHardenedAmisStatus'
const_no_value = 'AWSMS-NoValue'
ssm_user_provided_os_types = os.environ['SSMOfferingsUserProvidedOSTypes']
#ssm_wl_vpc_id = os.environ['SSMWorkloadVpcID']
ssm_rt_vol_encryption=os.environ['SSMRootVolumeEncryption']
ssm_retention_period=os.environ['SSMRetentionPeriod']
ddb_tbl_hrd_ami_crt = os.environ['DynamoTblFeatureHardenAMICreation']
customer_bucket = os.environ['CustomerBucket']
ssm_instance_types = os.environ['SSMInstanceTypes']
std_bucket = os.environ['StdBucket']
region = os.environ['StackRegion']

currentDT = datetime.now()
date_time= currentDT.strftime('%m-%d-%Y_%H%M%S')
offrng_supp_os_types = {
        'windows': {'Automation': 'QSCreateWinAMI', 'OS':'win'},
        'oracle-linux': {'Automation': 'QSCreateOracleLinuxAMI','OS':'oracle-linux'},
        'rhel': {'Automation': 'QSCreateRhelAMI','OS':'rhel'},
        'rhel9.0': {'Automation': 'rRhel90AMICreationAutomation','OS':'rhel9.0'},
        'suse': {'Automation': 'QSCreateSuseAMI','OS':'sles'},
        'ubuntu': {'Automation': 'QSCreateUbuntuAMI', 'OS':'ubuntu'},
        'amazon-linux': {'Automation': 'QSCreateAmazonLinuxAMI', 'OS':'amazon-linux'}
    }

def exec_ssm_automation(**args):
    try:
        automation_doc = args['AutomationDoc']
        ddb_tbl_hrd_ami_crt = args['DDB-Table']
        lambda_aws_request_id = args['LambdaRequestID']
        
        args.pop('AutomationDoc')
        args.pop('LambdaRequestID')
        args.pop('DDB-Table')
        if('win' not in args['OSName'][0] and 'CDSBucket' in args):
            args.pop('CDSBucket')
        
        # print(args)
        exec_id = boto_helper_obj.exec_ssm_automation_doc(automation_doc, args)
        now = datetime.now()
        
        ddb_item_json = {
             "SsmAutomationExecutionID": exec_id,
             "LambdaRequestID": str(lambda_aws_request_id),
             "AmiId": "",
             "OSName": args['OSName'][0] + '-' + args['OSArchitecture'][0] if 'OSArchitecture' in args else args['OSName'][0],
             "ExecutionStatus": "InProgress",
             "InstanceId": "",
             "CurrentStep":"",
             "CreationDate": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
             "LastModified": now.strftime("%Y-%m-%dT%H:%M:%SZ")
            }
        
        # print(ddb_tbl_hrd_ami_crt)
        boto_helper_obj.add_items(ddb_tbl_hrd_ami_crt, ddb_item_json)
        print('Record added to dynamodb table')
    except Exception as e:
        raise e
    
    
def lambda_handler(event, context):
    try:
        print('Event received- ',event)
        
        if ('RequestType' not in event):
            raise Exception('Not a event, expected events are {"RequestType": "CreateHardenedAmis"} or {"RequestType": "ViewCreateHardenedAmisStatus"}')
        bln_in_progress = False
        
        # Run the below code for Viewing the ssm Automation status and update the information in DyanmoDB table
        if(event['RequestType'] == 'ViewCreateHardenedAmisStatus'):
            for item in boto_helper_obj.get_dynamo_records(ddb_tbl_hrd_ami_crt):
                try:
                    exec_id = item['SsmAutomationExecutionID']
                    status = boto_helper_obj.get_ssm_auto_doc_status(exec_id)
                    instance_id, curr_step = boto_helper_obj.get_ssm_auto_doc_instance_id(exec_id)
                    if(instance_id):
                        boto_helper_obj.add_tag_to_instance(instance_id, item['OSName'], exec_id)
                        boto_helper_obj.update_dynamo_record(exec_id, status, ddb_tbl_hrd_ami_crt, None, instance_id, curr_step)
                        print('Record updated in DynamoDB. SsmAutomationExecutionID: {}, OSName: {}, current execution step: {}, InstanceId: {}'.format(exec_id, item['OSName'], curr_step, instance_id))
                    if(status != None and status != 'InProgress'):
                        output = boto_helper_obj.get_ssm_auto_doc_output(exec_id)
                        boto_helper_obj.update_dynamo_record(exec_id, status, ddb_tbl_hrd_ami_crt, output[0], None, curr_step)
                        print('Record updated in DynamoDB. SsmAutomationExecutionID: {}, OSName: {}, current execution step: {}, InstanceId: {}'.format(exec_id, item['OSName'], curr_step, instance_id))
                        if(instance_id and status != 'Success'):
                            print('SSM document execution status - {} ExecutionId - {}'.format(status, exec_id))
                            boto_helper_obj.terminate_instance(instance_id)
                    if(status == 'InProgress'):
                        bln_in_progress = True
                except Exception as e:
                    print(str(e))
                    print('ViewCreateHardenedAmisStatus is failed for ', item)
                    continue
            
            # Disable The rule - AWSMS-ViewCreateHardenedAmisStatus
            if(not bln_in_progress):
                boto_helper_obj.disable_event_rule(view_hardened_amis_rule)
                print('No InProgress excecutions available, Disabled rule - ',view_hardened_amis_rule)
                
            print('View Hardened Amis execution completed')
            
        if(event['RequestType'] == 'CreateHardenedAmis'):
            bln_create_exec = False
            lambda_aws_request_id = context.aws_request_id
            #wl_vpc_id = boto_helper_obj.get_ssm_param_values(ssm_wl_vpc_id)
            os_types = boto_helper_obj.get_ssm_param_values(ssm_user_provided_os_types)
            rt_vol_encrpt=boto_helper_obj.get_ssm_param_values(ssm_rt_vol_encryption)
            retention_period=boto_helper_obj.get_ssm_param_values(ssm_retention_period)
            # instance_types = json.loads(boto_helper_obj.get_ssm_param_values(ssm_instance_types).replace("'",'"'))
            
            #if(not boto_helper_obj.chk_ec2_key_pair(create_cust_ami_key_pair)):
                #boto_helper_obj.create_new_ec2_key_pair(customer_bucket, create_cust_ami_key_pair)
                
            #if(wl_vpc_id == const_no_value):
                #wl_vpc_id = boto_helper_obj.get_wl_vpc_id()
                #print('Workload VPC retrieved - ', wl_vpc_id)
            #else:
                #print('User provided Workload VPC ID ', wl_vpc_id)
                
            #sg_id = boto_helper_obj.get_def_sg(wl_vpc_id)
            #print('Default Security Group: ',sg_id)
            #subnet_id = boto_helper_obj.get_public_subnet(wl_vpc_id)
            #print('Public subnet: ',subnet_id)
            
            images = boto_helper_obj.get_s3_obj(customer_bucket)['Images']
            
            args = {}
            #args['SubnetId'] = [subnet_id]
            #args['KeyName'] = [create_cust_ami_key_pair]
            #args['SecurityGroup'] = [sg_id]
            args['CDSBucket'] = [std_bucket]
            args['Environment'] = ['Production']
            args['DDB-Table'] = ddb_tbl_hrd_ami_crt
            args['LambdaRequestID'] = lambda_aws_request_id
            args['Encryption'] = [rt_vol_encrpt]
            args['RetentionPeriod']=[retention_period]
            
            # print('Insatnce Types - ', instance_types)
            
            if('windows' in os_types.lower()):
                os_verions = [image['OS'] for image in images if image['Region'] == region and offrng_supp_os_types['windows']['OS'] in image['OS'].lower()]
                ami_list = { image['OS']: image['ImageId'] for image in images if image['Region'] == region 
                                    and 'ImageId' in image
                                    and offrng_supp_os_types['windows']['OS'] in image['OS'].lower()}
                
                instance_types = { image['OS']: image['InstanceType'] for image in images if image['Region'] == region 
                                    and 'InstanceType' in image
                                    and offrng_supp_os_types['windows']['OS'] in image['OS'].lower()}

                os_verions.remove(offrng_supp_os_types['windows']['OS'])
    
                args['AutomationDoc'] = boto_helper_obj.get_automation_doc_arn(offrng_supp_os_types['windows']['Automation'])
                for os in os_verions:
                    try:
                        print('Started executing for OS - ', os)
                        os_ver = os.replace('win', '')
                        args['AvailableSourceAmiId'] = ['{ver} : {ami}'.format(ver=os_ver, ami=ami_list[os])]
                        args['SourceAmiId'] =[ami_list[os]]
                        args['OSName'] = [os]
                        args['TargetAmiName'] = ['QS-CoRE-WINDOWS-v{}-{}'.format(os_ver,date_time)]
                        args['InstanceType'] = [instance_types[os]]
                        exec_ssm_automation(**args)
                        print('Execution successful - ',os)
                        bln_create_exec = True
                    except Exception as e:
                        print('Failed execution - ', str(e))
                        continue
    
            
            if('amazon' in os_types.lower()):
                os_verions = [image['OS'] for image in images if image['Region'] == region and offrng_supp_os_types['amazon-linux']['OS'] in image['OS'].lower()]
                ami_list = { image['OS']: image['ImageId'] for image in images if image['Region'] == region 
                                    and 'ImageId' in image
                                    and offrng_supp_os_types['amazon-linux']['OS'] in image['OS'].lower()}
                
                instance_types = { image['OS']: image['InstanceType'] for image in images if image['Region'] == region 
                                    and 'InstanceType' in image
                                    and offrng_supp_os_types['amazon-linux']['OS'] in image['OS'].lower()}
                                    
                if 'AvailableSourceAmiId' in args:
                    args.pop('AvailableSourceAmiId')
                ami_list.pop(offrng_supp_os_types['amazon-linux']['OS'])
                os_verions.remove(offrng_supp_os_types['amazon-linux']['OS'])
                
                args['AutomationDoc'] = boto_helper_obj.get_automation_doc_arn(offrng_supp_os_types['amazon-linux']['Automation'])
                arch = None
                print(instance_types)
                for os in os_verions:
                    print(os)
                    try:
                        print('Started executing for OS - ', os)
                        if 'arm' in os:
                            os_name = os.replace('-arm','')
                            os_ver = os + '64'
                            arch = 'arm64'
                        elif ('x86' in os):
                            os_name = os.replace('-x86','')
                            os_ver = os + '_64'
                            arch = 'x86_64'
                        else:
                            os_name = os
                            os_ver = os
        
                        args['SourceAmiId'] =[ami_list[os]]
                        args['OSName'] = [os_name]
                        args['TargetAmiName'] = ['QS-CoRE-{}-{}'.format(os_ver,date_time)]
                        args['InstanceType'] = [instance_types[os]]
                        if(arch):
                            args['AvailableSourceAmiId'] = ['{ver} : {ami}'.format(ver=os_ver, ami=ami_list[os])]
                            args['OSArchitecture'] = [arch]
                        else:
                            args['SourceAmiId'] = ['{ami}'.format(ami=ami_list[os])]
                        exec_ssm_automation(**args)
                        print('Execution successful - ',os)
                        bln_create_exec = True
                    except Exception as e:
                        print('Failed execution - ', str(e))
                        continue

            if ('OSArchitecture' in args):
                args.pop('OSArchitecture')

            if ('SourceAmiId' in args):
                args.pop('SourceAmiId')
            
            if ('AvailableSourceAmiId' in args):
                args.pop('AvailableSourceAmiId')
            
            if('oracle' in os_types.lower()):
                os_verions = [image['OS'] for image in images if image['Region'] == region and offrng_supp_os_types['oracle-linux']['OS'] in image['OS'].lower()]
                ami_list = { image['OS']: image['ImageId'] for image in images if image['Region'] == region 
                                    and 'ImageId' in image
                                    and offrng_supp_os_types['oracle-linux']['OS'] in image['OS'].lower()}
                                    
                instance_types = { image['OS']: image['InstanceType'] for image in images if image['Region'] == region 
                                    and 'InstanceType' in image
                                    and offrng_supp_os_types['oracle-linux']['OS'] in image['OS'].lower()}
               
                ami_list.pop(offrng_supp_os_types['oracle-linux']['OS'])
                os_verions.remove(offrng_supp_os_types['oracle-linux']['OS'])
                args['AutomationDoc'] = boto_helper_obj.get_automation_doc_arn(offrng_supp_os_types['oracle-linux']['Automation'])
                for os in os_verions:
                    os_ver = os.replace('oracle-linux', 'OL')
                    executed = {}
                    try:
                        print('Started executing for OS - ', os)
                        args['SourceAmiId'] =  [ami_list[os]]
                        args['AvailableSourceAmiId'] = ['{ver} : {ami}'.format(ver=os_ver, ami=ami_list[os])]
                        args['OSName'] = [os]
                        args['TargetAmiName'] = ['QS-CoRE-{}-{}'.format(os,date_time)]
                        args['InstanceType'] = [instance_types[os]]
                        exec_ssm_automation(**args)
                        print('Execution successful - ',os)
                        bln_create_exec = True
                    except Exception as e:
                        print('Failed execution - ', str(e))
                        continue
                    
            if('ubuntu' in os_types.lower()):
                os_verions = [image['OS'] for image in images if image['Region'] == region and offrng_supp_os_types['ubuntu']['OS'] in image['OS'].lower()]
                ami_list = { image['OS']: image['ImageId'] for image in images if image['Region'] == region 
                                    and 'ImageId' in image
                                    and offrng_supp_os_types['ubuntu']['OS'] in image['OS'].lower()}
                
                instance_types = { image['OS']: image['InstanceType'] for image in images if image['Region'] == region 
                                    and 'InstanceType' in image
                                    and offrng_supp_os_types['ubuntu']['OS'] in image['OS'].lower()}
                                    
                ami_list.pop(offrng_supp_os_types['ubuntu']['OS'])
                os_verions.remove(offrng_supp_os_types['ubuntu']['OS'])
                args['AutomationDoc'] = boto_helper_obj.get_automation_doc_arn(offrng_supp_os_types['ubuntu']['Automation'])
                for os in os_verions:
                    try:
                        os_ver = os.replace('ubuntu', '')
                        args['SourceAmiId'] = [ami_list[os]]
                        args['AvailableSourceAmiId'] = ['{ver}:{ami}'.format(ver=os, ami=ami_list[os])]
                        args['OSName'] = [os]
                        args['TargetAmiName'] = ['QS-CoRE-{}-{}'.format(os,date_time)]
                        args['InstanceType'] = [instance_types[os]]
                        exec_ssm_automation(**args)
                        print('Execution successful - ',os)
                        bln_create_exec = True
                    except Exception as e:
                        print('Failed execution - ', str(e))
                        continue

            if('rhel' in os_types.lower()):
                os_verions = [image['OS'] for image in images if image['Region'] == region and offrng_supp_os_types['rhel']['OS'] in image['OS'].lower()]
                ami_list = { image['OS']: image['ImageId'] for image in images if image['Region'] == region 
                                    and 'ImageId' in image
                                    and offrng_supp_os_types['rhel']['OS'] in image['OS'].lower()}
                
                instance_types = { image['OS']: image['InstanceType'] for image in images if image['Region'] == region 
                                    and 'InstanceType' in image
                                    and offrng_supp_os_types['rhel']['OS'] in image['OS'].lower()}
                #print(ami_list)
                ami_list.pop('rhel')
                #print(os_verions)
                os_verions.remove('rhel')
                for os in os_verions:
                    try:
                        os_ver = os.replace('rhel', '')
                        if('rhel9.0' in os):
                            args['AutomationDoc'] = boto_helper_obj.get_automation_doc_arn(offrng_supp_os_types['rhel9.0']['Automation'])
                            args['AvailableSourceAmiId'] = ['{ver}:{ami}'.format(ver=os, ami=ami_list[os])]
                        else:
                            args['AutomationDoc'] = boto_helper_obj.get_automation_doc_arn(offrng_supp_os_types['rhel']['Automation'])
                            args['AvailableSourceAmiId'] = ['{ver}:{ami}'.format(ver=os, ami=ami_list[os])]
                        args['SourceAmiId'] = [ami_list[os]]
                        args['OSName'] = [os]
                        args['TargetAmiName'] = ['QS-CoRE-{}-{}'.format(os,date_time)]
                        args['InstanceType'] = [instance_types[os]]
                        exec_ssm_automation(**args)
                        print('Execution successful - ',os)
                        bln_create_exec = True
                    except Exception as e:
                        print('Failed execution - ', str(e))
                        continue
            
            if('suse' in os_types.lower() or 'sles' in os_types.lower()):
                os_verions = [image['OS'] for image in images if image['Region'] == region and offrng_supp_os_types['suse']['OS'] in image['OS'].lower()]
                ami_list = { image['OS']: image['ImageId'] for image in images if image['Region'] == region 
                                    and 'ImageId' in image
                                    and offrng_supp_os_types['suse']['OS'] in image['OS'].lower()}
                
                instance_types = { image['OS']: image['InstanceType'] for image in images if image['Region'] == region 
                                    and 'InstanceType' in image
                                    and offrng_supp_os_types['suse']['OS'] in image['OS'].lower()}
                # print(instance_types)
                ami_list.pop('sles')
                os_verions.remove('sles')
                args['AutomationDoc'] = boto_helper_obj.get_automation_doc_arn(offrng_supp_os_types['suse']['Automation'])
                for os in os_verions:
                    executed = {}
                    try:
                        args['AvailableSourceAmiId'] = ['{ver} : {ami}'.format(ver=os, ami=ami_list[os])]
                        args['SourceAmiId'] = [ami_list[os]]
                        args['OSName'] = [os]
                        args['TargetAmiName'] = ['QS-CoRE-{}-{}'.format(os,date_time)]
                        args['InstanceType'] = [instance_types[os]]
                        exec_ssm_automation(**args)
                        print('Execution successful - ',os)
                        bln_create_exec = True
                    except Exception as e:
                        print('Failed execution - ', str(e))
                        continue
            if(bln_create_exec):
                # Enable the CW rule AWSMS-ViewCreateHardenedAmisStatus
                boto_helper_obj.enable_event_rule(view_hardened_amis_rule)
                print('Enabled events rule - ', view_hardened_amis_rule)
            else:
                print('No ssm automations executed.')
            print('Create Hardened Amis execution completed')
    except Exception as e:
        print('Lambda execution failed ',e)
