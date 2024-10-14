'''
Native Backup Monitoring : Implemented via AWSPE- 6608

The function gets triggered based on an EventBridge rule. The EventBridge rule looks for the AWS backup job state change. 
If the job state is ABORTED or FAILED, then the function will be invoked.
If the service name is valid, then a json payload will be created and sns publish will be performed to create an incident in the SNOW.
The priority of the incident can be modified in the AccountFeatureDefinitions table, under the respective feature items. 

sample event:
{

   "id":"",
   "detail-type":"",
   "account":"",
   "time":"",
   "region":"",
   "resources":[
      
   ],
   "detail":{
      "backupJobId":"",
      "resourceArn":"",
      "resourceType":"",
      "state":"",
   }
}

'''
import os
from dynamodb_helper import dynamodb_helper
from s3_helper import s3_helper
from rds_helper import rds_helper

dynamodb_obj = dynamodb_helper()
s3_obj = s3_helper()
rds_obj = rds_helper()

sns_topic = os.environ['SNS_TOPIC']
afd_table = os.environ['AFD_TABLE']
val_to_fetch = 'pfSnowInciPriority'

def lambda_handler(event, context):
    
    try:
        print('Event received - ',event)
        service_name = event['detail']['resourceArn'].split(":")[2]
        print("The service name is - ", service_name)
        
        if 'dynamodb' in service_name.lower():
            dynamodb_obj.create_json_payload_and_sns_publish(event,sns_topic,afd_table,val_to_fetch)
        elif 's3' in service_name.lower():
            s3_obj.create_json_payload_and_sns_publish(event,sns_topic,afd_table,val_to_fetch)
        elif "rds" in service_name.lower():
            rds_obj.create_json_payload_and_sns_publish(event,sns_topic,afd_table,val_to_fetch)            
        else:
            print("Not a valid service. Hence skipping the process")            
        
    except Exception as e:
        print("Error - ", e)