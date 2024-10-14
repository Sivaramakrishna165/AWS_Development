
# Implemented via AWSPE- 5781
# Acceptance Criteria:

# STEP 5 StateMachineMMSummaryReport

# This is the last state for Makemanage
# If all state machine steps are successful, set the dxc_make_manage tag on the instance to "Managed"
# If there is an error, write "Failure" to  InstanceReport DynamoDB table

# Send the Generated report to S3 Customer bucket and update CSV
# For reporting - we will have one csv report in the customer bucket and each make manage run will append the instance to the report.


import boto3, csv, os, datetime
import codecs
from botocore.config import Config
from boto3.dynamodb.conditions import Key

class UpdateItemException(Exception):
    pass

class generate_mm_summary_report():
    def __init__(self, region='us-east-1'):
        self.config = Config(retries=dict(max_attempts=10,mode='standard'))

        currentDT = datetime.datetime.now()
        self.date_time= currentDT.strftime('%m_%d_%Y_%H%M%S')

        self.ddb = boto3.resource('dynamodb', config=self.config)
        self.ddb_inst_info = os.environ['ddbInstInfoTableName']
        self.ddb_inst_rep = os.environ['ddbInstRepTableName']
        self.ddb_param_set = os.environ['ddbParamSetTableName']

        self.ec2_resource = boto3.resource('ec2', config=self.config)
        self.ec2_client = boto3.client('ec2', config=self.config)
        self.s3_resource = boto3.resource('s3', config=self.config) 
        self.s3_client = boto3.client('s3', config=self.config) 
        self.ssm_client = boto3.client("ssm", config=self.config)

        MakeManageLastStateName = os.environ['ppMakeManageLastStateName']
        MakeManageOutputLocationName = os.environ['ppMakeManageOutputLocationName']
        self.customerBucket = os.environ['pDXCS3CustomerBucketName']
        
        self.makeManageLastStateName = self.ssm_client.get_parameter(Name = MakeManageLastStateName,
                                        WithDecryption=True)['Parameter']['Value']
        self.makeManageOutputLocation = self.ssm_client.get_parameter(Name = MakeManageOutputLocationName,
                                        WithDecryption=True)['Parameter']['Value']
        print(self.makeManageOutputLocation)
        self.output_folder = '/'.join(self.makeManageOutputLocation.split('/')[:-1])
        self.output_file_name = self.makeManageOutputLocation.split('/')[-1]

    # Update records to table - FtMakeManageInstancesReport
    def update_report_table(self, instance_id, status):
        try:
            table = self.ddb.Table(self.ddb_inst_rep)
            currentDT = datetime.datetime.now()
            date_time = currentDT.strftime('%m-%d-%Y_%H%M%S')
            
            table.update_item(
                Key={
                    'InstanceId': instance_id
                },
                UpdateExpression='SET ModifyTime=:time,StateSuccessFail=:status',
                ExpressionAttributeValues={
                    ':time': date_time,
                    ':status': status
                }
            )
            print('Report Table - {} updated successfully for insatnceId - {}'.format(self.ddb_inst_rep, instance_id))
        except boto3.exceptions.botocore.client.ClientError as e:
            print("Error updating item: %s" % e)
            raise UpdateItemException("Error: %s" % e) 

    def updateMMTag(self,instanceId, key, status):
        """
        """
        if status == 'SUCCESS':
            self.update_tag(instanceId, key, 'Managed')
        else:
            self.update_tag(instanceId, key, 'Fail')

    def update_tag(self, resource, key, value):
        try:
            update_tag_response = self.ec2_client.create_tags(
                Resources=[
                    resource,
                ],
                Tags=[
                    {
                        'Key': key,
                        'Value': value
                    },
                ]
            )
            print('Instance - {}, tag:{} updated - {}'.format(resource, key, value))
        except Exception as e:
            print("Error in update_tag", e)

    def getReportData(self,instanceId):
        """
        """
        ddb_inst_rep_table_obj = self.ddb.Table(self.ddb_inst_rep)
        #Boto3 Get All Items aka Scan
        # response = table.scan()
        # instance_csv_data = response['Items']
        response = ddb_inst_rep_table_obj.get_item(Key={
                    'InstanceId': instanceId
                })
        instance_report_data = response['Item']
        return instance_report_data

    def create_latest_report_list(self,instanceId):
        """
        """
        try:
            instance_report_data = self.getReportData(instanceId)
            self.updateMakemanageS3ReportFile(instance_report_data)
            return instance_report_data
        except Exception as e:
            print(e)
            raise

    # Read s3 object
    def read_s3_object(self, bucket, key):
        try:
            print(key)
            data = self.s3_client.get_object(Bucket=bucket, Key=key)
            return data
        except Exception as e:
            print('Error read_s3_object() -',e)
            raise

    def report_line(self,instance_report_data):
        report = []
        summary_output = {}
        for k,v in instance_report_data.items():
            summary_output[k] = v
        report.append(summary_output)
        print('Report - ', report)
        return report 

    def updateMakemanageS3ReportFile(self,instance_report_data):
        """
        """
        output_s3_path = self.output_folder + '/' + self.output_file_name
        instance_csv_data = []
        try:
            instance_csv_data = self.read_s3_object(self.customerBucket, output_s3_path)
        except Exception as e:
            print(str(e))

        print("#####################")
        print(instance_report_data)
        print("#####################")
        keys = self.report_line(instance_report_data)[0].keys()
        print(keys)
        with open('/tmp/'+self.output_file_name, 'a', newline='') as output_file:
            dict_writer = csv.DictWriter(output_file, keys)
            dict_writer.writeheader()
            try:
                if instance_csv_data:
                    for row in csv.DictReader(codecs.getreader("utf-8")(instance_csv_data["Body"])):
                        print(" ############### OLD Data START HERE ###############")
                        print(row)
                        print(" ############### OLD Data END HERE ###############")
                        dict_writer.writerows(self.report_line(row))
                dict_writer.writerows(self.report_line(instance_report_data))
            except Exception as e:
                print(e)
                raise

        print("before s3_upload_object")
        print("self.output_folder is ", self.output_folder)
        print("output_s3_path is ", output_s3_path)
        print("self.bucket is ", self.customerBucket)
        print("self.output_file_name is ", self.output_file_name)
        tmpfile = '/tmp/'+self.output_file_name
        print("tmpfile is ", tmpfile)
        print("############################# UPLOAD SUCCESSFUL START #########################")
        self.s3_resource.meta.client.upload_file(tmpfile,self.customerBucket,output_s3_path)
        os.remove(tmpfile)
        print("############################# UPLOAD SUCCESSFUL END #########################")