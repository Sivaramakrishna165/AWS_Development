'''
This Lambda script updates the attributes in DynamoDB
'''

import boto3
import os,sys

# generic lambda function to update Dynamo DB by passing below arguments
# - patch_job_id
# - field_name
# - field_value


def PrintException():
    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    captureErr = "Line No. : " + str(lineno)  + " | ERROR: " + str(exc_obj)
    return captureErr

        
def create_itemData_dynamoDB(patchJob_id,attributeKey,attributeValue):
    try:
        print("Patch_JOB_ID : ",patchJob_id)
        print("attribute_key : ",attributeKey)
        print("attributeValue : ",attributeValue)
        dynamodb = boto3.resource('dynamodb')
        updateAttribute = "set " + attributeKey + "=:data"
        print("update_attribute : ",updateAttribute)
        patch_table = dynamodb.Table('Ft_dxcms_patching_e2e_automation')        
        patch_table.update_item(
                Key={'patchJob_id': patchJob_id},
                UpdateExpression=updateAttribute,
                ExpressionAttributeValues={':data': attributeValue},
                ReturnValues="UPDATED_NEW"
                ) 
    except:
        print(PrintException())


def lambda_handler(event,context):
    print("Event : ",event)
    patchJob_id = event['patchJob_id']
    attributeKey = event['attribute_name']
    attributeValue = event['attribute_value']
    create_itemData_dynamoDB(patchJob_id,attributeKey,attributeValue)
    return event

event1 = {
  "patchJob_id": "patchJobId_634e18d2-019c-11ec-a79e-624bb59c47bf",
  "attribute_name": "Change_Request",
  "attribute_value": "CHG0094437"
}
    
if __name__ == "__main__":
    lambda_handler(event1,"")
