'''
Boto Helper class contain all the supported aws api operations
'''

import boto3
from botocore.config import Config
from datetime import datetime

class recovery_boto_helper():
    
    #To add the item to the dynamodb table    
    def add_instance_info_item(self, tbl_name, item_json, ddb_resource):
        
        try:
            table = ddb_resource.Table(tbl_name)
            table.put_item(Item=item_json)
            print("Item added to the table-",tbl_name)
            return True
        
        except Exception as e:
            print("ERROR adding item: {}  - {}".format(item_json, str(e)))
            return False