'''
This lambda function is used to generate Unique ID to trigger step function.
'''
import uuid

from datetime import datetime

# def fetch_current_time():
#     now = datetime.now()
#     current_time = now.strftime("%d%m%Y%H%M%S")
#     return current_time

def lambda_handler(event,context):
    print("Event : ",event)
    # name = str(fetch_current_time())
    execution_id = str(uuid.uuid1())
    Name = "SFN_Name_" + execution_id
    event['SubSFName'] = Name
    return event


# simple test cases
if __name__ == "__main__":
    event1 = {"S3_Bucket": "dxc","S3_directory_name": "MAY_2021"}   
    lambda_handler(event1, "")








