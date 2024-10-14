'''
NOTE: Lambda function name will be dynamically allocated while stack creation

Lambda function is invoked by rCicdInitiateProcessLambda function.
Function is used to CREATE/DEPLOY stacks. And the same is recorded in DynamoDB table - *rCicdStacksReportDdbTable*
And enables Event rule - *rdxcCICDReportRule* for checking the stack creation status

Created By: Kedarnath Potnuru
Date: 14 Apr 2023

'''

import json
import boto3
import os
import datetime
from boto_helper import boto_helper

cicd_report_tbl = os.environ['CICDReportDbdTable'].split('/')[-1]
cross_acc_role = os.environ['CrossAccountRole']
cicd_report_event_rule = os.environ['CICDReportRule'].split('/')[-1]
s3_cfn_path = 'https://s3.{}.amazonaws.com/{}/{}'
currentDT = datetime.datetime.now()
date_time= currentDT.strftime('%m%d%Y%H%M%S')

def construct_parameter(param_json):
    try:        
        return [{'ParameterKey':param, 'ParameterValue':param_json[param]} for param in param_json]
    except Exception as e:
        print('Error: construct_parameter() -', e)
        raise
        
def lambda_handler(event, context):
    
    try:
        print('Event received',event)
        # print('Context received',context)
        
        template_key = event['Template']
        template_config_key = event['Configuration']
        pipeline = event['Pipeline']
        bucket = event['Bucket']
        region = context.invoked_function_arn.split(':')[3]
        deploy_region = os.environ['Region']
        
        if(deploy_region == ''): deploy_region = region
        
        helper_obj = boto_helper(pipeline, deploy_region, cross_acc_role)
        ddb_json = {}
        ddb_json['Status'] = 'Failed'
        ddb_json['StackDescription'] = ''
        try:
            cft_name = ''
            cft_params = None
            
            if('' != template_config_key):
                template_config = helper_obj.get_s3_object(bucket, template_config_key)
                if('StackName' in template_config and template_config['StackName'].strip() != ''):
                    cft_name = template_config['StackName']
                if('Parameters' in template_config):
                    cft_params = template_config['Parameters']
                if('ParentStack' in template_config and template_config['ParentStack'].strip() != ''):
                    print(f'{cft_name} is a child/nested stack')
                    return 'Lambda Execution complete'

            if('' == cft_name):
                cft_name = template_key.split('/')[-1].split('.')[0]
            
            stack_status = helper_obj.bln_check_stack_exists(cft_name)
            if(stack_status != None):
                # Update logic comes here
                if('complete' in stack_status.lower()):
                    
                    change_set = {}
                    change_set['StackName'] = cft_name
                    if(cft_params not in ['', None]):
                        change_set['Parameters'] = construct_parameter(cft_params)
                    change_set['TemplateURL'] = s3_cfn_path.format(region, bucket, template_key)
                    change_set['ChangeSetName'] = cft_name+'-' + date_time
                    
                    res_change_set = helper_obj.create_stack_change_set(change_set)
                    curr_change_set = helper_obj.describe_change_set(change_set)
                    
                    if(len(curr_change_set)>0):
                        helper_obj.execute_change_set(res_change_set['Id'], cft_name)
                        ddb_json['StackName'] = cft_name
                        ddb_json['Status'] = 'UPDATE_INPROGRESS'
                        ddb_json['Comments'] = 'Stack update initiated'
                        helper_obj.add_items(cicd_report_tbl, ddb_json)
                        print('Stack "{}" UPDATE initiated'.format(cft_name))
                        helper_obj.enable_event_rule(cicd_report_event_rule)
                        
                    else:
                        print('Stack "{}" update not applicable. No changeset found.'.format(cft_name))
                    
                elif('create_failed' in stack_status.lower()):
                    pass
                    # Cleanup logic comes here
                else:
                    ddb_json['Status'] = stack_status
                    raise Exception('Stack "{}" is in "{}" state'.format(cft_name, stack_status))
            else:
                print(f'"{cft_name}" - Stack does not exists')
                stack_params = {}
                stack_params['StackName'] = cft_name
                if(cft_params not in ['', None]):
                    stack_params['Parameters'] = construct_parameter(cft_params)
                    
                stack_params['TemplateURL'] = s3_cfn_path.format(region, bucket,template_key)
                helper_obj.create_stack(stack_params)
                ddb_json['StackName'] = cft_name
                ddb_json['Status'] = 'InProgress'
                ddb_json['Comments'] = 'Stack creation initiated'
                helper_obj.add_items(cicd_report_tbl, ddb_json)
                
                print('Stack "{}" CREATE initiated'.format(cft_name))
                
                helper_obj.enable_event_rule(cicd_report_event_rule)
                
        except Exception as e:
            print('Error while create/update ',e)
            ddb_json['StackName'] = cft_name
            ddb_json['Comments'] = str(e)
            
            helper_obj.add_items(cicd_report_tbl, ddb_json)
            
        return {
            'statusCode': 200,
            'body': json.dumps('Hello from Lambda!')
        }
    
    except Exception as e:
        print('Error ', e)
        raise e
