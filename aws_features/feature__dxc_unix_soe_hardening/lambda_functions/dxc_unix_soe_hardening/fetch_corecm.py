import json
import boto3
import response
s3_client = boto3.client('s3', region_name = 'us-east-1')


def handler(event, context):
    type = event['ResourceProperties']['Type']
    print('EVENT:[{}]'.format(event))
    responseData = {}
    if event['RequestType'] == "Delete":
        response.send(event,context,response.SUCCESS,responseData)
        return
    responseData = {}
    try:
        OSArch = event['ResourceProperties']['OSArch']
        s3response = s3_client.list_objects_v2(
        Bucket= event['ResourceProperties']['CoreCMBucket'],
        Prefix=event['ResourceProperties']['Prefix'])
        if(type == "fedora"):
            if(OSArch == "aarch64"):
                coreCMList = list(filter(getCoreCMFedoraARM,s3response['Contents']))
                coreCMList.sort(key=lambda x : x['LastModified'],reverse=True)
                print(coreCMList)
                retVal = coreCMList[0]['Key'].replace('corecm/arm/','')
            elif(OSArch == "x86_64"):
                coreCMList = list(filter(getCoreCMFedora,s3response['Contents']))
                coreCMList.sort(key=lambda x : x['LastModified'],reverse=True)
                print(coreCMList)
                retVal = coreCMList[0]['Key'].replace('corecm/x86/','')
        elif(type == "debian"):
            coreCMList = list(filter(getCoreCMDebian,s3response['Contents']))
            coreCMList.sort(key=lambda x : x['LastModified'],reverse=True)
            print(coreCMList)
            retVal = coreCMList[0]['Key'].replace('corecm/x86/','')
        responseData['CoreCMPackage'] = retVal
        print(responseData)
        response.send(event, context, response.SUCCESS, responseData)
    except Exception as e:
        responseData['error'] = str(e)
        response.send(event,context,response.FAILED,responseData)

def getCoreCMFedoraARM(item):
    if(item['Key'] !='corecm/arm/' and  item['Key'].find('Ubuntu') == -1 and  item['Key'].find('ARM') != -1):
        return True
    else:
        return False

def getCoreCMFedora(item):
    if(item['Key'] !='corecm/x86/' and  item['Key'].find('Ubuntu') == -1 and  item['Key'].find('ARM') == -1):
        return True
    else:
        return False
#ubuntu
def getCoreCMDebian(item):
    if(item['Key'] !='corecm/x86/' and  item['Key'].find('Ubuntu') != -1):
        return True
    else:
        return False
