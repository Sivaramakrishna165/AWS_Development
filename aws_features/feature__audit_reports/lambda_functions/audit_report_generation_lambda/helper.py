import boto3,json
import datetime
import os
import time
from boto3.dynamodb.conditions import Key, Attr

from botocore.config import Config

class helper():

    def __init__(self):

        self.currentDT = datetime.datetime.now()
        self.Date_time= self.currentDT.strftime("%Y%m%d_%H%M%S")

        config=Config(retries=dict(max_attempts=10,mode='standard'))
        self.s3_client_obj = boto3.client('s3',config=config)
        self.sns = boto3.client('sns', config=config)

    def create_s3_file(self,bucket_name,final_report,folder,filename):

        try:

            s3path = folder+"/" + filename

            data_file = open('/tmp/'+filename, 'w+')
            data_file.write(str(final_report))
            data_file.close()   

            self.s3_client_obj.upload_file('/tmp/'+filename, bucket_name , s3path) 

            print('file creation in s3 completed. Bucket:{a} | Folder:{b} | File:{c}'.format(a=bucket_name,b=folder,c=filename))

        except Exception as e:
            print('error in create_s3_file():',e)
            raise
    
    # method will read the data from ADS Dynamo Db table to get the object
    def get_db_object(self,table,feature_name,val_to_fetch):
        try:
            response = table.query(KeyConditionExpression=Key('Feature').eq(feature_name))

            for item in response['Items']:
                fetched_object = item['FeatureParams'][val_to_fetch]['Default']
                print('fetched_object:',fetched_object)

            return fetched_object
        except Exception as e:
            print('error in get_db_object():',e)
            raise
    
    def send_to_snow(self,message,snow_topic):
        try:
            result = self.sns.publish(
                             TopicArn=snow_topic,
                             Message=json.dumps(
                                         {'default': json.dumps(message)}
                                     ),
                             MessageStructure='json',
                             Subject=('AWS Audit Reports')
                         )
        
        except Exception as e:
            print('error in send_to_snow():',e)
            raise