'''
Boto Helper class contain all the supported aws api operations
'''

import boto3, json
from botocore.config import Config

class boto_helper():
    
    def __init__(self):
        config = Config(retries=dict(max_attempts=10,mode='standard'))
        self.ssm_client = boto3.client('ssm', config=config)
    
    def check_document(self,doc_name):
        try:

            self.ssm_client.describe_document(Name=doc_name)
               
            return True
        except self.ssm_client.exceptions.InvalidDocument:
            return False
        except Exception as e:
            print('Error check_document()-',str(e))
            raise 

    def delete_document(self,doc_name):
        try:
            self.ssm_client.delete_document(
                                            Name=doc_name,
                                            Force=True )
            print("deleted SessionManagerRunShell document successfully")
        except Exception as e:
            print('Error delete_document()-',str(e))
            raise 
