import boto3,json
import datetime
import os
import time
from botocore.exceptions import ClientError
import uuid

from botocore.config import Config

class sechub_export():
    def __init__(self):

        self.currentDT = datetime.datetime.now()
        self.Date_time= self.currentDT.strftime("%Y%m%d_%H%M%S")

        config=Config(retries=dict(max_attempts=10,mode='standard'))
        self.s3_client = boto3.client('s3',config=config)
        #self.s3_resource = boto3.client('s3',config=config)
    
    def get_findings(self,bucket,object_key):
        record_count = 0
        try:
            response = self.s3_client.get_object(Bucket=bucket, Key=object_key)
            findings = '['+ response['Body'].read().decode('utf-8').replace('}{','},\n{') +']'
            
            findings_list = json.loads(findings)

            return findings_list
        
        except Exception as e:
            print('error in get_findings():',e)
            raise
    
    def process_findings(self,findings_list, region, account):
        try:
            
            output = {}
            
            for item in findings_list:
                # For native AWS Services.  GuardDuty,Security Hub, Access Analyzer
                # have been tested.
                product_type = item['resources'][0].split('/')[3]
                if product_type.startswith('arn:aws'):
                    product_node = item['resources'][0].split('/')[3]
                    #print(f'product node is {product_node}')
                    product = product_node.split(':')
                    product_name = product[2]
                    region = product[3]
                    account_id = product[4]
                # Handle default and 3rd party product. Cloud Custodian falls into this category
                # Other integrated product may have format that can cause problem
                else:
                    product_name = item['resources'][0].split('/')[2]
                    region = region #item['resources'][0].split('/')[3]
                    account_id = account #item['resources'][0].split('/')[4]
                key = account_id + '/' + product_name + '/'+region
                #print( f'key is {key}')
                # Ensure Athena compatibility, remove '-' from 'detail-type'
                item['detailType'] = item['detail-type']
                item.pop('detail-type', None)
                if key not in output:
                    output[key] = [item]
                else:
                    output[key].append(item)
            
            return output
        
        except Exception as e:
            print('error in process_findings():',e)
            raise
        
    def create_s3_object(self,output,S3_BUCKET,partition,object_name):
        try:
            
            for key in output:
                
                s3path = 'AWSLogs/'+ key +'/'+partition  + '/'  + object_name + '.json'
                s3path_csv = 'AWSLogs/'+ key +'/'+partition  + '/'  + object_name + '.csv'
                temp_path = '/tmp/'+'findings_temp_file.json'
                temp_path_csv = '/tmp/'+'findings_temp_csv_file.csv'
                body = ''
                csv_body = ''
                
                csv_data = 'Title|Description|ProductArn|ProductName|Resource_Id|CreatedAt|Severity_Level|RecordState|WorkflowState'+'\n'
                
                for version in output[key]:
                    body += json.dumps(version) + '\n'
                    
                    for row in version['detail']['findings']:
                        #print('row:',row)
                        row_data=''
                        data_list = [str(row['Title']),str(row['Description']),str(row['ProductArn']),str(row['ProductName']),str(row['Id']),str(row['CreatedAt']),str(row['Severity']['Label']),str(row['RecordState']),str(row['WorkflowState'])]
                        row_data = '|'.join(data_list)
                        csv_data+= str(row_data) + '\n'
                        
                with open(os.path.join('/tmp', 'findings_temp_file.json'), 'w') as file:
                    json.dump(body,file)
                    
                data_file = open(os.path.join('/tmp', 'findings_temp_csv_file.csv'), 'w+')
                data_file.write(str(csv_data))
                data_file.close() 

                files = os.listdir('/tmp')
                print('Temp file writing is completed',files)

                self.s3_client.upload_file(temp_path, S3_BUCKET , s3path,ExtraArgs={"ServerSideEncryption": "AES256"} )
                self.s3_client.upload_file(temp_path_csv, S3_BUCKET , s3path_csv,ExtraArgs={"ServerSideEncryption": "AES256"} )
        
        except Exception as e:
            print('error in create_s3_object():',e)
            raise

class sechub_historicaldata_export():
    def __init__(self):

        self.currentDT = datetime.datetime.now()
        self.Date_time= self.currentDT.strftime("%Y%m%d_%H%M%S")

        config=Config(retries=dict(max_attempts=10,mode='standard'))
        self.s3_client = boto3.client('s3',config=config)
        self.sechub_client = boto3.client('securityhub',config=config)
        self.ssm_client = boto3.client('ssm',config=config)
        
        self.S3_BUCKET = os.environ['S3_BUCKET']
        self.SSM_PARAMETER_COUNT = os.environ['SSM_PARAMETER_COUNT']
        
    def create_filter(self):
        finding_filter = {
                    "RecordState": [
                        {
                            "Value": "ACTIVE",
                            "Comparison": "EQUALS"
                        },
                    ]
                }
        return finding_filter
    
    def get_findings (self, finding_filter):
        
        results=[]
        extra_args = {}
        extra_args['Filters'] = finding_filter
        extra_args['MaxResults'] = 100

        print("Running export for Security Hub findings...")
        try:
            while True:
                response = self.sechub_client.get_findings( **extra_args )
                results.extend(response["Findings"])

                if('NextToken' in response):
                    extra_args['NextToken'] = response['NextToken']
                else:
                    print("NextToken not found. Ending Security Hub finding export.")
                    break

            print('final len of results:',len(results))
            return results
        
        except ClientError as error_handle:
            if error_handle.response['Error']['Code'] == 'TooManyRequestsException':
                time.sleep(5)
                print('Catching Security Hub API Throttle...')
        except Exception as e:
            print('Error in get_findings',e)
            
    def put_obj_to_s3(self,results):
        key = datetime.datetime.now().strftime('%Y/%m/%d/%H') + "/security-hub-finding-export" + str(uuid.uuid4()) + ".json"
        csv_key = datetime.datetime.now().strftime('%Y/%m/%d/%H') + "/security-hub-finding-export" + str(uuid.uuid4()) + ".csv"
        try:
            print("Exporting {} findings to s3://{}/{}".format(len(results), self.S3_BUCKET, key))

            folder = 'historicaldata'
            s3path = folder+"/" + key
            s3path_csv = folder+"/" + csv_key
            temp_path = '/tmp/'+'temp_file.json'
            temp_path_csv = '/tmp/'+'csv_temp_file.csv'
            
            
            with open(os.path.join('/tmp', 'temp_file.json'), 'w') as file:
                json.dump(results,file)

            csv_data = 'Title|Description|ProductArn|ProductName|Resource_Id|CreatedAt|Severity_Level|RecordState|WorkflowState'+'\n'
            for row in results:
                row_data=''
                data_list = [str(row['Title']),str(row['Description']),str(row['ProductArn']),str(row['ProductName']),str(row['Id']),str(row['CreatedAt']),str(row['Severity']['Label']),str(row['RecordState']),str(row['WorkflowState'])]
                row_data = '|'.join(data_list)
                csv_data+= str(row_data) + '\n'
            
            data_file = open(os.path.join('/tmp', 'csv_temp_file.csv'), 'w+')
            data_file.write(str(csv_data))
            data_file.close() 
            
            files = os.listdir('/tmp')
            print('files after write:',files)
            
            self.s3_client.upload_file(temp_path, self.S3_BUCKET , s3path,ExtraArgs={"ServerSideEncryption": "AES256"} )
            self.s3_client.upload_file(temp_path_csv, self.S3_BUCKET , s3path_csv,ExtraArgs={"ServerSideEncryption": "AES256"} )
            
            print("Successfully exported {} findings to s3://{}/{}".format(len(results), self.S3_BUCKET, key))
            
        except ClientError as error_handle:
            if error_handle.response['Error']['Code'] == 'ConnectTimeoutError':
                time.sleep(5)
                print('Catching Connection Timeout Error...')
            raise
        except Exception as exception_handle:
            print('error in put_obj_to_s3:',exception_handle)
            raise
    
    def sechub_count_value (self,results):
        print("Adding {} Security Hub findings to export count...".format(len(results)))
        try: 
            existing_value = self.ssm_client.get_parameter(
                Name=self.SSM_PARAMETER_COUNT
            )
            existing_value['Parameter']['Value']
            sechub_count = (int(existing_value['Parameter']['Value'])) + len(results)
            response = self.ssm_client.put_parameter(
                Name=self.SSM_PARAMETER_COUNT,
                Value= str(sechub_count),
                Overwrite=True,
            )
            print("Current Security Hub export count is {}.".format(str(sechub_count)))
            
            return sechub_count
        except ClientError as error_handle:
                print('error in sechub_count_value:',error_handle)
                raise