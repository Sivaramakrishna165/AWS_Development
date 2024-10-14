import boto3
import sys
import os, json
from botocore.config import Config
from boto3.dynamodb.conditions import Key
from datetime import datetime

class boto_helper():
    def __init__(self):
        config=Config(retries=dict(max_attempts=10,mode='standard'))
        self.ec2_client = boto3.client('ec2', config = config)
        self.s3_client = boto3.client('s3', config = config)
        self.s3_resource = boto3.resource('s3', config = config)
        self.ssm_client = boto3.client('ssm',config=config)
        self.ddb = boto3.resource('dynamodb', config=config)
        self.events_client = boto3.client('events',config=config)
    
    def add_tag_to_instance(self, instance_id, os, exec_id):
        try:
            name = 'FeatureCreateHardenedAmis-'+os
            tags = [{ 'Key':'Name', 'Value':name}, {'Key':'Owner', 'Value':'DXC'}, {'Key':'Application', 'Value':'AWS Managed Services'},
                    {'Key':'SSM-Automation-ExecutionId', 'Value' : exec_id}]
            self.ec2_client.create_tags(Resources=[instance_id], Tags=tags)
        except Exception as e:
            print('add_tag_to_instance() error ', e)
    
    
        # Upload s3 object/report
    def s3_upload_object(self,filename, bucket, s3path):
        try:
            self.s3_client.upload_file(filename, bucket , s3path)
        except Exception as e:
            print('Error s3_upload_object() -',e)
            raise
    
    # Returns true on Successful execution of describe key pair
    """def chk_ec2_key_pair(self, key_pair):
        try:
            self.ec2_client.describe_key_pairs(KeyNames=[key_pair])
            print('EC2 Key Pair - "{}" already available in the AWS account '.format(key_pair))
            return True        
        except Exception as e:
            if ('NotFound' in str(e)): return None
            raise"""
    
    def disable_event_rule(self, rule_name):
        try:
            self.events_client.disable_rule(Name=rule_name)
        except Exception as e:
            print('Error - disable_event_rule() ',e)
            
    def enable_event_rule(self, rule_name):
        try:
            self.events_client.enable_rule(Name=rule_name)
        except Exception as e:
            print('Error - enable_rule() ',e)
            
    def terminate_instance(self, instance_id):
        try:
            self.ec2_client.terminate_instances(
                InstanceIds=[
                    instance_id
                ]
            )
            print('Terminate Instance executed - ', instance_id)
        except Exception as e:
            print('Terminate Instance Failed - ',e)
        
    """def create_new_ec2_key_pair(self, bucket, key_pair):
        try:
            output_automation_key_pair = open(('/tmp/'+key_pair)+'.pem','w')
            key_pair_path = 'feature-automation-create-custom-ami/ec2-keypair/' + key_pair + '.pem'
            response = self.ec2_client.create_key_pair(KeyName=key_pair)
            i = response['KeyMaterial']
            output_automation_key_pair.write(i)
            output_automation_key_pair.close()
            os.chmod(('/tmp/'+key_pair)+'.pem', 400)
            self.s3_upload_object('/tmp/'+key_pair+'.pem', bucket, key_pair_path)
            
            print('New ec2 key-pair "{k}" is created and pem file - {k}.pem'.format(k=key_pair))
        except Exception as e:
            raise"""
    
        # Get Workload VPC ID
    """def get_wl_vpc_id(self):
        try:
            chk_tags = ['Workload VPC v2', 'Workload VPC', 'Customer VPC']
            response = self.ec2_client.describe_vpcs()
            for vpc in response['Vpcs']:
                wl_tag_val = [tag['Value'] for tag in vpc['Tags'] if 'Name' in tag['Key']]
                if(wl_tag_val and wl_tag_val[0] in chk_tags):
                    return vpc['VpcId']
            raise Exception('NO VPCs found')
        except:
            raise"""
    
        # Get the default subnet of the VPC
    """def get_def_sg(self, vpc_id):
        try:
            res = self.ec2_client.describe_security_groups(
                Filters=[
                            {
                                'Name': 'vpc-id',
                                'Values': [vpc_id
                                ]
                            },
                        ])
            return [sg['GroupId'] for sg in res['SecurityGroups'] if sg['Description'] == 'default VPC security group'][0]
        except:
            raise"""
    
    # Get the public subnet in a VPC
    """def get_public_subnet(self, vpc_id):
        try:
            resp_subnets = self.ec2_client.describe_subnets(
                                            Filters=[
                                                {
                                                    'Name': 'vpc-id',
                                                    'Values': [
                                                        vpc_id,
                                                    ]
                                                },
                                            ],
                                        )
            for subnet in resp_subnets['Subnets']:
                resp_rt = self.ec2_client.describe_route_tables(
                    Filters=[
                        {
                            'Name': 'association.subnet-id',
                            'Values': [
                                subnet['SubnetId'],
                            ]
                        },
                    ],
                )

                for rt in resp_rt['RouteTables']:
                    routes = [obj for obj in rt['Routes'] if 'GatewayId' in obj and 'igw' in obj['GatewayId']]
                    if(routes): # If IGW is not there in routes then it is a Private subnet
                        return subnet['SubnetId']
            return False
        except:
            raise"""
    
    def get_ssm_param_values(self, ssm_param = None):    
        try:
            response = self.ssm_client.get_parameter(Name=ssm_param)
            return response['Parameter']['Value']
        except self.ssm_client.exceptions.ParameterNotFound:
            raise(Exception('SSM Parameter Not found - {}'.format(ssm_param)))
        except Exception as e:
            print('get_ssm_param_values() error:', e)
    
    def add_items(self, tbl_name, obj_json):
        try:
            table = self.ddb.Table(tbl_name)
            print(obj_json)
            table.put_item(Item=obj_json)
            # print(response)
        except boto3.exceptions.botocore.client.ClientError as e:
            print("Error adding item: {}  - {}".format(obj_json, str(e)))
            raise
        
    
    # Get S3 object content
    def get_s3_obj(self, bucket, key='deploy/utilities/ami-catalog.json'):
        try:
            content_object = self.s3_resource.Object(bucket, key)
            file_content = content_object.get()['Body'].read().decode('utf-8')
            json_content = json.loads(file_content)
            return json_content
        except:
            raise
        
        # Start the ssm document for the given document name and params
    def exec_ssm_automation_doc(self, doc_name, params):
        try:
            response = self.ssm_client.start_automation_execution(DocumentName=doc_name, Parameters=params)
            return response['AutomationExecutionId']
        except Exception as e:
            print(str(e))
            raise
            
    
        # Get the ssm document for the given OS type
    def get_automation_doc_arn(self, doc_name):
        try:
            extra_args = {}
            extra_args['Filters']=[{'Key': 'Owner', 'Values': ['Self']}]
            next_token = '' 
            output_document = []
            while True:
                response = self.ssm_client.list_documents(**extra_args)
                for doc in response['DocumentIdentifiers']:  
                    if(doc_name.lower() in doc['Name'].lower()):
                        return doc['Name']
                if('NextToken' in response):
                    extra_args['NextToken'] = response['NextToken']
                else:
                    break
            return output_document       
        except:
            raise
        
    def get_ssm_auto_doc_instance_id(self, execution_id):
        try:
            response = self.ssm_client.get_automation_execution(AutomationExecutionId=execution_id)
            curr_step = [stage['StepName'] for stage in response['AutomationExecution']['StepExecutions'] if stage['StepStatus'] in ['InProgress','Cancelled','Failed','TimedOut']]
            if(len(curr_step) == 0): curr_step = ['All Steps Executed']
            launch_inst_step = response['AutomationExecution']['StepExecutions'][0]
        
            if 'InstanceIds' in launch_inst_step['Outputs']:
                return launch_inst_step['Outputs']['InstanceIds'][0], curr_step[0]
            else:
                return None, curr_step[0]
        except Exception as e:
            print('get_ssm_auto_doc_instance_id() error ',str(e))
            return None
            
    def get_ssm_auto_doc_status(self, execution_id):
        try:
            response = self.ssm_client.get_automation_execution(AutomationExecutionId=execution_id)
            return response['AutomationExecution']['AutomationExecutionStatus']
        except Exception as e:
            print('get_ssm_auto_doc_status() error - ',str(e))
            return None
    
    def get_ssm_auto_doc_output(self, execution_id):
        try:
            response = self.ssm_client.get_automation_execution(AutomationExecutionId=execution_id)
            if('createImage.ImageId' in response['AutomationExecution']['Outputs']):
                return response['AutomationExecution']['Outputs']['createImage.ImageId']
            if('CreateImage.ImageId' in response['AutomationExecution']['Outputs']):
                return response['AutomationExecution']['Outputs']['CreateImage.ImageId']
            return response['AutomationExecution']['Outputs']
        except Exception as e:
            print('get_ssm_auto_doc_output() error - ',str(e))
            return None
            
    def update_dynamo_record(self, exec_id, status, tbl_name, ami=None, instanceid=None, curr_step=None):
        try:
            table = self.ddb.Table(tbl_name)
            now = datetime.now()
            time = now.strftime("%Y-%m-%dT%H:%M:%SZ")
            
            UpdateExpression = "set "
            ExpressionAttributeValues = {}
            UpdateExpression = UpdateExpression + " ExecutionStatus=:s,"
            UpdateExpression = UpdateExpression + " LastModified=:t,"
            UpdateExpression = UpdateExpression + " CurrentStep=:cs,"
            ExpressionAttributeValues[':t'] = time
            ExpressionAttributeValues[':s'] = status
            ExpressionAttributeValues[':cs'] = curr_step
            
            if(ami):
                UpdateExpression = UpdateExpression + "AmiId=:id,"
                ExpressionAttributeValues[':id'] = ami
                
            if(instanceid):
                UpdateExpression = UpdateExpression + "InstanceId=:i,"
                ExpressionAttributeValues[':i'] = instanceid
            
            UpdateExpression = UpdateExpression[:-1]
            
            response = table.update_item(
                Key={
                    'SsmAutomationExecutionID': exec_id
                },
                UpdateExpression=UpdateExpression,
                ExpressionAttributeValues=ExpressionAttributeValues,
                ReturnValues="UPDATED_NEW"
            )
            return response
        except boto3.exceptions.botocore.client.ClientError as e:
            print("Error updating item: {}".format(str(e)))
            raise

    def get_dynamo_records(self, tbl_name):
        table = self.ddb.Table(tbl_name)
        try:
            scan_kwargs  = { 'FilterExpression': Key('ExecutionStatus').eq(str('InProgress'))}
            done = False
            start_key = None
            # check for pagination key, if present make another scan for next page
            while not done:
                if start_key:
                    scan_kwargs['ExclusiveStartKey'] = start_key
    
                response = table.scan(**scan_kwargs)
                start_key = response.get('LastEvaluatedKey', None)
    
                # ensure there's data and fetch another page
                data = response['Items']
                if data:
                    # iterate through each result in the page
                    for item in data:
                        yield item
    
                done = start_key is None
            
        except boto3.exceptions.botocore.client.ClientError as e:
            print("Error adding item: {}".format(str(e)))
            raise