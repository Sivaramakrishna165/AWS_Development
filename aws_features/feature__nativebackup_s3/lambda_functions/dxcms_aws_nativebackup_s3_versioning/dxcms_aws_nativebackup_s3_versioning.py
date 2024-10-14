'''
[AWSPE-6585]
This is a custom lambda function, fetches the buckets that contains the backup tag key and checks whether versnioning is enabled or not.
If not, then the versioning will be enabled on the buckets.

The event that is passed to this lambda typically looks like this:

{
   "RequestType":"",
   "ServiceToken":"",
   "StackId":"",
   "RequestId":"",
   "LogicalResourceId":""
}
'''

import json
import os
import boto3
from boto_helper import boto_helper

boto_obj = boto_helper()
tag_key = os.environ['TagValue']

def handler(event,context):
    
    if 'source' in event and event['source'] == 'aws.tag':        
        print("The trigger is from event bridge rule")
        print("event received-", event)
        bucketarn=event['resources'][0]
        bucketname=bucketarn.split(":")[5]
        print("bucketname-", bucketname)
        
        s3_versioning_status=boto_obj.get_s3_bucket_versioning_status(bucketname)
        print(s3_versioning_status)
        if 'Status' in s3_versioning_status:
            if s3_versioning_status['Status'] != 'Enabled':
                print("version is suspended. Hence enabling the versioning on bucket", bucketname)
                enable_version = boto_obj.s3_enable_versioning(bucketname)
            else:
                print("version is already enabled on the bucket", bucketname)
        else:
            print("Versioning is not enabled. Hence enabling the versioning on bucket", bucketname)
            enable_version = boto_obj.s3_enable_versioning(bucketname)
    else:
        print("The request is from stack")
        
        try:
            print('event received-', event)
            response = {}
            response['Status'] = 'SUCCESS'
            response['Reason'] = 'See the details in CloudWatch Log Stream: ' + context.log_stream_name
            response['PhysicalResourceId'] = context.log_stream_name
            response['StackId'] = event['StackId']
            response['RequestId'] = event['RequestId']
            response['LogicalResourceId'] = event['LogicalResourceId']
            response['NoEcho'] = False
    
            if (event['RequestType'] in ['Create']) and ('ServiceToken' in event):
                try:
                    tagkey=tag_key.split("/")[1]
                    s3_bucket_list = []
                    s3_buckets=boto_obj.fetch_s3_bucket()
                    for bucket in s3_buckets:
                        try:
                            s3_bucket_with_tags=boto_obj.fetch_s3_bucket_with_tag(bucket['Name'])
                            for tag in s3_bucket_with_tags['TagSet']:
                                if tagkey in tag['Key']:
                                    s3_bucket_list.append(bucket['Name'])
                        except:
                            pass
                    print("The s3 bucket list with tags are -", s3_bucket_list)
    
                    for bucket in s3_bucket_list:
                        try:
                            s3_versioning_status=boto_obj.get_s3_bucket_versioning_status(bucket)
                            if 'Status' in s3_versioning_status:
                                if s3_versioning_status['Status'] != 'Enabled':
                                    print("version is suspended. Hence enabling the versioning on bucket", bucket)
                                    enable_version = boto_obj.s3_enable_versioning(bucket)
                                else:
                                    print("version is already enabled on the bucket", bucket)
                            else:
                                print("Versioning is not enabled. Hence enabling the versioning on bucket", bucket)
                                enable_version = boto_obj.s3_enable_versioning(bucket)
                        except Exception as e:
                            print(e)
    
                    boto_obj.send_response(event, response, status='SUCCESS', reason='Lambda Completed')
                    
    
    
                except Exception as e:
                    print('Error', e)
                    response['Error'] = str(e)
                    boto_obj.send_response(event, response, status='FAILED', reason=str(e))
    
            if (event['RequestType'] in ['Delete','Update']) and ('ServiceToken' in event):
                    boto_obj.send_response(event, response, status='SUCCESS', reason='Delete/Update event received')
            
            return {
                'statusCode': 200,
            }
    
        except Exception as e:
            print("Lambda Execution Error",e)
            raise