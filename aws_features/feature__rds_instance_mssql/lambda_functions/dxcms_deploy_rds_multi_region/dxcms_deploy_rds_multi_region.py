import json
import boto3
import os
from uuid import uuid4
from botocore.config import Config
import http.client
import urllib.parse
import yaml


def create_stack(client,stack_name,template_url,parameters):
    try:
        response = client.create_stack(StackName=stack_name,TemplateURL=template_url,
                        Parameters=parameters,Tags=[{'Key': "Owner",'Value': "DXC"}], 
                        Capabilities=['CAPABILITY_IAM'], OnFailure='DO_NOTHING')
        print("RDS multi region stack is creating in secondary region")
        return True
    except Exception as e:
        print("Error-create_stack()",e)
        return str(e)

def update_parameter(client, ssm_param, value):
    try:
        client.put_parameter(Name=ssm_param,Value=value,Type='String',Overwrite=True)
    except Exception as e:
        print("Error-update_parameter",e)

def get_parameter(client, ssm_param):
    try:
        response = client.get_parameter(Name=ssm_param)
        return response['Parameter']['Value']
    except Exception as e:
        print("Error-get_parameter()",e)
        return None

def delete_cft(client,stack_name):
    try:
        response = client.delete_stack(StackName=stack_name)
    except Exception as e:
        print("ERROR-delete_cft()",e)

def get_object_yaml(boto_resource, bucket, key):
    try:
        response = boto_resource.get_object(Bucket=bucket, Key=key)
        if 'Body' in response:
            file = response['Body'].read()
            template = yaml.load(file, Loader=yaml.BaseLoader)
            return template
        else:
            return None
    except Exception as e:
        print("error-get_object_yaml()",e)

def describe_stack(client,stack):
    try:
        response = client.describe_stacks(StackName=stack)
        if response['Stacks']:
            return "Stack present"
        else:
            return None
    except Exception as e:
        return None
"""

def invoke_lambda(client,function,payload):
    try:
        response = client.invoke(FunctionName=function,InvocationType='Event',Payload=bytes(json.dumps(payload), encoding='utf8'))
    except Exception as e:
        print("Error-invoke_lambda()",e)

def get_stack_resource(client,stack_name,logical_name):
    try:
        response = client.describe_stack_resources(
        StackName=stack_name,
        LogicalResourceId=logical_name
        )
        
        return response['StackResources'][0]['PhysicalResourceId']
    except Exception as e:
        print("Error-get_stack_resource",e)  
        """

def send_response(request, response, status=None, reason=None):
    try:
        if status is not None:
            response['Status'] = status
        if reason is not None:
            response['Reason'] = reason
        if 'ResponseURL' in request and request['ResponseURL']:
            try:
                url = urllib.parse.urlparse(request['ResponseURL'])
                body = json.dumps(response)
                print('Body - ', body)
                https = http.client.HTTPSConnection(url.hostname)
                https.request('PUT', url.path + '?' + url.query, body)
                print('HTTP response sent successfully')
            except:
                print("Failed to send the response to the provided URL")
        return response
    except Exception as e:
        print("Error-send_response()",e)


def lambda_handler(event, context):
    try:
        print("Received Event-",event)
        secondary_region=os.environ['SECONDARY_REGION']
        primary_region=os.environ['AWS_REGION']
        s3_bucket=os.environ["SECONDARY_BUCKET_NAME"]
        #failover_lambda_logical_id="rDxcmsRDSMultiRegionDRFailoverLambda"

        config=Config(retries=dict(max_attempts=10,mode='standard'))
        secondary_cft_client=boto3.client('cloudformation',region_name=secondary_region,config=config)
        secondary_region_ssm_client=boto3.client('ssm',region_name=secondary_region,config=config)
        #secondary_region_lambda_client=boto3.client('lambda',region_name=secondary_region,config=config)

        primary_region_ssm_client=boto3.client('ssm',region_name=primary_region,config=config)
        primary_region_s3_client=boto3.client('s3',region_name=primary_region,config=config)


        response={}
        if (event['RequestType'] in ['Create','Update','Delete']) and ('ServiceToken' in event):            
            response['Status'] = 'SUCCESS'
            response['Reason'] = 'See the details in CloudWatch Log Stream: ' + context.log_stream_name
            response['PhysicalResourceId'] = context.log_stream_name
            response['StackId'] = event['StackId']
            response['RequestId'] = event['RequestId']
            response['LogicalResourceId'] = event['LogicalResourceId']
            response['NoEcho'] = False
            response['Data'] = {}
        if event['RequestType'] in ['Delete']:
            ssm_param=event['ResourceProperties']["ssm_param"]
            param_value=get_parameter(primary_region_ssm_client,ssm_param)
            stack_name=json.loads(str(param_value).replace("'",'"'))["stack_name"]

            #delete_cft(secondary_cft_client,stack_name)
            #print("Deleted multi-region rds stack in secondary region")

            send_response(event, response, status='SUCCESS', reason='Delete event received')
        else:
            secondary_region=os.environ['SECONDARY_REGION']
            primary_region=os.environ['AWS_REGION']
            s3_key=os.environ['S3_KEY']
            s3_template_key=os.environ['S3_KEY'].replace("lambda_functions","resource_deployment/RDSInstanceMssqlMultiRegion.yaml")
            
            if str(s3_bucket).lower()=="none":
                s3_bucket="dxc.prod.obe.standards.601716130897.{}".format(secondary_region)
            feature_name=os.environ["FEATURE_NAME"]
            common_servicenow_topic=os.environ["COMMON_SERVICENOW_TOPIC"]
            
            #table_name="AccountFeatureDefinitions"
            parameters=[]

            try:
                ssm_param=event['ResourceProperties']["ssm_param"]
                param_value=get_parameter(primary_region_ssm_client,ssm_param)
                ssm_stack_name=json.loads(str(param_value).replace("'",'"'))["stack_name"]

                if (event['RequestType'] in ['Update']):

                    if str(describe_stack(secondary_cft_client,ssm_stack_name)).lower()=="stack present":
                        print("RDS Multi region stack Already present in the secondary region")
                        if 'ResourceProperties' in event:
                            db_identifier=event['ResourceProperties']["db_identifier"]
                            sec_vpc=event['ResourceProperties']["sec_vpc"]
                            sec_db_identifier=event['ResourceProperties']["sec_db_identifier"]
                            sec_sg_id=event['ResourceProperties']["sec_sg_id"]
                            opt_grp=event['ResourceProperties']["opt_grp"]
                            param_grp=event['ResourceProperties']["param_grp"]
                            inst_cls=event['ResourceProperties']["inst_cls"]
                            cw_log=event['ResourceProperties']["cw_log"]
                            al_strg=event['ResourceProperties']["al_strg"]
                            iam_auth=event['ResourceProperties']["iam_ath"]
                            db_name=event['ResourceProperties']["db_name"]
                            multi_az=event['ResourceProperties']["multi_az"]
                            pr_sns_topic=event['ResourceProperties']["pr_sns_topic"]
                            storage_type=event['ResourceProperties']["strg_type"]
                            ssm_param="/DXC/RDS-MSSQL/PRIMARY/TABLE/ITEMS-"+ssm_stack_name.split("-")[5]
                            ssm_db_item={"secondary_vpc_id":sec_vpc,
                                    "secondary_source_sg":sec_sg_id,
                                    "db_identifier":db_identifier,
                                    "db_option_gp_name":opt_grp,
                                    "db_instance_class":inst_cls,
                                    "db_cw_logs":cw_log,
                                    "db_parameter_group":param_grp,
                                    "db_allocatedstorage":str(al_strg),
                                    "db_iam_authentication":iam_auth,
                                    "db_name":db_name,
                                    "db_multi_az":multi_az,
                                    "primary_sns_topic":pr_sns_topic,
                                    "secondary_db_identifier":sec_db_identifier,
                                    "storage_type":storage_type}
                            #param_value=json.loads(str(get_parameter(secondary_region_ssm_client,ssm_param)).replace("'",'"'))
                            #params_change=[]
                            update_parameter(secondary_region_ssm_client,ssm_param,str(ssm_db_item))
                            print("Updated parameter",ssm_param)
                            #params_change.extend(param  for param in ["db_option_gp_name","db_instance_class","db_cw_logs","db_parameter_group","db_allocatedstorage","db_iam_authentication","db_multi_az"] if param_value[param]!=ssm_db_item[param])
                            #if params_change:
                                #failover_lambda=get_stack_resource(secondary_cft_client,ssm_stack_name,failover_lambda_logical_id)
                                #invoke_lambda(secondary_region_lambda_client,failover_lambda,{"update_rds":params_change})

                        send_response(event, response, status='SUCCESS', reason='Lambda Invoked')
                        return None
                        exit()
            except:
                pass
            #secondary_s3_client=boto3.client("s3",region_name=secondary_region)
            
            db_identifier=event['ResourceProperties']["db_identifier"]
            
           
            object_url="https://s3.{}.amazonaws.com/{}/{}".format(secondary_region,s3_bucket,s3_template_key)
            
            #s3_template=get_object_yaml(primary_region_s3_client,s3_bucket_name,s3_template_key)

            stack_name='Feature-RDSInstanceMssql-Multi-region-stack-{}'.format(str(uuid4()))
            ssm_param=event['ResourceProperties']["ssm_param"]
            json_obj={"stack_name":stack_name}
            update_parameter(primary_region_ssm_client,ssm_param,str(json_obj))

            parameters=[{'ParameterKey':"pPrimaryRegion",'ParameterValue':primary_region},{'ParameterKey':"pcommonserviceNowTopic",'ParameterValue':common_servicenow_topic},{'ParameterKey':"pFeatureName",'ParameterValue':feature_name},{'ParameterKey':"pDXCS3BucketName",'ParameterValue':s3_bucket},{'ParameterKey':"pDXCS3KeyPrefix",'ParameterValue':s3_key},{'ParameterKey':"pDBIdentifier",'ParameterValue':db_identifier},{'ParameterKey':"pSecondaryresources",'ParameterValue':stack_name}]

            stack_status=create_stack(secondary_cft_client,stack_name,object_url,parameters)
            
            if stack_status==True:
                send_response(event, response, status='SUCCESS', reason='Lambda Invoked')
            else:
                send_response(event, response, status="FAILED", reason=stack_status)

    except Exception as e:
        print("Error-lambda_handler()",e)
        if (event['RequestType'] in ['Create','Update','Delete'] and 'ServiceToken' in event):
            send_response(event, response, status='SUCCESS', reason='Delete event received')
    
