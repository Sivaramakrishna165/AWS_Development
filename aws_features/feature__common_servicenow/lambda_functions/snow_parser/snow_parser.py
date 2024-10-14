import boto3
import json
import os
from botocore.config import Config

#Example Snow Parser event received
#{'Records': [{'messageId': 'c295049d-11ed-4bd4-8af3-8b41bb61be68', 'receiptHandle': 'AQEBnivXW891HooVwCYxEaX9SOIjEHgyqmpbiX62vZs6JYfq5M8TNfGrHDEJoxSQpKs+Tjx6oPg4ATZ0ky/1Ab3jMx26DP5ywP82TKqtMZPUwDa8Pd10eWCoAJvKqQ0Wm4QJv9ATQH+YEljmGeoO/cY3lTWvgeK9M2fp5nht2BO107A+ADlNeRMk9YhGB5y5mMsKO49Sv5NHHUJZrZfVAMEPVZ2KSX0S7O0QwX5P0KaXttosBDAe74SDkiyP7mbldyCjG2V/hV9rqW4ABp8FKQh35vXkUc2cyaNCIsJXGxRlzm/CD0L29OxvT9tvcNCDegZ5exTX7v9X75J3joPIaRbxmjp1RyvNT32WTHFQPqDTzGD+dvK+h5yK5Aw/JchZRbYTzCy+UoC/ZCY9GEBF6Y4ZAG6QP0FLovKcXzyyWP8+jm9MHsPG5XrIuW0riQJweXN6M3JycssUIPR6T6A6luL2KLZgiovlDNeiIWcv9ruGZhQ=', 'body': '{\n  "Type" : "Notification",\n  "MessageId" : "22fb7a5f-08e5-5985-b45f-2179c634e63d",\n  "TopicArn" : "arn:aws:sns:us-west-1:225992052696:FeatureCommonServicenowStack-Servicenow-NT6WBTJ0FBAW-rStdInputTopic-2IMDC1B5CGGK",\n  "Message" : "{\\"default\\": \\"required for json format\\", \\"Trigger\\": {\\"MetricName\\": \\"Config Service: Non-Compliance\\", \\"Dimensions\\": [{\\"name\\": \\"InstanceId\\", \\"value\\": \\"i-0abbb1ebbb73f188c\\"}], \\"EvaluateLowSampleCountPercentile\\": \\"\\", \\"ComparisonOperator\\": \\"GreaterThanThreshold\\", \\"TreatMissingData\\": \\"\\", \\"Statistic\\": \\"SampleCount\\", \\"StatisticType\\": \\"Statistic\\", \\"Period\\": \\"3600\\", \\"EvaluationPeriods\\": \\"1\\", \\"Unit\\": \\"event_Unit\\", \\"Namespace\\": \\"ConfigEvaluations\\", \\"Threshold\\": \\"0\\", \\"Region\\": \\"us-east-2\\"}, \\"original_Timestamp\\": \\"2022-06-01T01:02:03.000Z\\", \\"AlarmName\\": \\"FeatureConfigNotificationSe-rSendNotificationState-ABC123\\", \\"AlarmDescription\\": \\"Non-Compliant Config Resources\\", \\"NewStateReason\\": \\"Non-Compliant Resources: [{\'ResourceId\': \'i-0abbb1ebbb73f188c\', \'Notification\': \'false\', \'ResourceType\': \'AWS::EC2::Instance\', \'ConfigRuleName\': \'FeatureConfigRuleEBSInstanceStack-EB-AWSConfigRule-ABC123\'}, {\'ResourceId\': \'i-0abbb1ebbb73f188c\', \'Notification\': \'false\', \'ResourceType\': \'AWS::EC2::Instance\', \'ConfigRuleName\': \'FeatureConfigRuleApprovedAmisStack-A-AWSConfigRule-ABC123\'}, {\'ResourceId\': \'i-0abbb1ebbb73f188c\', \'Notification\': \'false\', \'ResourceType\': \'AWS::EC2::Instance\', \'ConfigRuleName\': \'FeatureConfigRuleEc2InstanceDetaile-rAWSConfigRule-ABC123\'}, {\'ResourceId\': \'vol-03485c5a5f5c4228e\', \'Notification\': \'false\', \'ResourceType\': \'AWS::EC2::Volume\', \'ConfigRuleName\': \'FeatureConfigRuleEbsVolumeStack-EbsV-AWSConfigRule-ABC123\'}, {\'ResourceId\': \'vol-03485c5a5f5c4228e\', \'Notification\': \'false\', \'ResourceType\': \'AWS::EC2::Volume\', \'ConfigRuleName\': \'FeatureConfigRuleEbsSnapshotStack-Eb-AWSConfigRule-ABC123\'}]\\", \\"AWSAccountId\\": \\"225992052696\\", \\"Region\\": \\"us-east-2\\", \\"OldStateValue\\": \\"OK\\", \\"NewStateValue\\": \\"ALARM\\", \\"MessageId\\": \\"event_MessageId\\", \\"PriorityData\\": {\\"Priority\\": \\"1\\"}}",\n  "Timestamp" : "2022-06-17T18:48:49.282Z",\n  "SignatureVersion" : "1",\n  "Signature" : "DGF6zaWZovHldWKoq5iRauM1gKDcY9q8PS8i5I66866LcPSbeQM9L6xHNYCSeM0UNJbk9VTLt2eUl26m4AjBtlpVaqy9Cof5dajj7d2JqucVcyJoe9NszPnhtfbKzYoJxFlx3n9xDK5uPZl6UcVyxBZeWhd2bRCeQQgalOGn1a3bpy5E5hLa4sOxOBZXIwsL2PvT62PDLQZqTcAvd60ExMtzUdtV1MeN6ig8gMDK41Zp1F6Vh/LnHtQ5U6yKODKwJbe5d3iD8Kc6no9hO7nY4qBTcUMQoVpCUy4pamkzWl0loms5P+yLb/iDlQEATWLT75IRMRxwRX7jVnH8yaEC4g==",\n  "SigningCertURL" : "https://sns.us-west-1.amazonaws.com/SimpleNotificationService-7ff5318490ec183fbaddaa2a969abfda.pem",\n  "UnsubscribeURL" : "https://sns.us-west-1.amazonaws.com/?Action=Unsubscribe&SubscriptionArn=arn:aws:sns:us-west-1:225992052696:FeatureCommonServicenowStack-Servicenow-NT6WBTJ0FBAW-rStdInputTopic-2IMDC1B5CGGK:83697949-edb4-4ba4-9471-a15dd52834d7"\n}', 'attributes': {'ApproximateReceiveCount': '1', 'SentTimestamp': '1655491729314', 'SenderId': 'AIDAJKV7U6VPUEF2G77MA', 'ApproximateFirstReceiveTimestamp': '1655491729316'}, 'messageAttributes': {}, 'md5OfBody': 'f7e1238112f72eeebefcfb64ec24071e', 'eventSource': 'aws:sqs', 'eventSourceARN': 'arn:aws:sqs:us-west-1:225992052696:FeatureCommonServicenowStack-Servicenow-NT6WBTJ0FBA-rSqsParserQueue-jdmpyUCjpujN', 'awsRegion': 'us-west-1'}]}

config=Config(retries=dict(max_attempts=4,mode='standard'))
lambda_client = boto3.client('lambda',config=config)
sqs_client = boto3.client('sqs',config=config)
ssm_client = boto3.client('ssm',config=config)

AwsRegion = os.environ['Aws_Region']
AwsAccount = os.environ['Aws_Account']
Dlq_Url = os.environ['DLQ_URL']
domain_name_param=os.environ["Domain_name"]
business_service_param=os.environ["Business_service"]
customer_name_param=os.environ["Customer_name"]
aws_account_name_param=os.environ["aws_account_name_param"]

# Severity(Urgency)     Impact > 1=Critical   2=High   3=Medium   4=Low
# 1=Critical/Critical            1=Critical   2=High   3=Medium   3=Medium 
# 2=High/Major                   2=High       2=High   3=Medium   3=Medium
# 3=Medium/Minor                 3=Medium     3=Medium 3=Medium   4=Low
# 4=Low/Warning/Normal           4=Low        4=Low    4=Low      4=Low

# format message for Agnostic API

def format_agnostic_msg(msg, lambda_send_name, event_time, Dlq_Url):
    try:
        print("msg in format_msg is ", msg)
        print("AwsAccount in format_agnostic_msg is ", AwsAccount)

        if 'EventList' in msg:
            ### process Agnostic message
            #     if already formatted for Agnostic API, use it
            print("Processing Agnositc API items in EventList")
            for item in msg['EventList']:
                agnostic_msg = {}
                # use existing severity and incidentImpact if present, otherwise, use PriorityData input field
                priority_fields = set_priority(msg)
                print("priority_fields are ", priority_fields)
                print("item in msg['EventList'] is ", item)
                fixed_category = 'AWS CloudWatch'
                fixed_incidentCategory = 'Integration'
                fixed_incidentSubcategory = 'Data'
                long_description = get_longdescription(msg)
                resourceid = get_resourceid(msg,long_description)
                relatedcihints = resourceid
                agnostic_msg_event_list_json = {}
                agnostic_msg_event_list = []
                agnostic_msg_event_list_json['AWSAccountId'] = AwsAccount 
                if 'eventsourcesendingserver' in item:
                    agnostic_msg_event_list_json['eventsourcesendingserver'] = item['eventsourcesendingserver']
                if 'eventsourceexternalid' in item:
                    agnostic_msg_event_list_json['eventsourceexternalid'] = item['eventsourceexternalid']

                agnostic_msg_event_list_json['severity'] = priority_fields['severity']
                agnostic_msg_event_list_json['incidentImpact'] = priority_fields['incidentImpact']

                if 'title' in item:
                    titlemsg = get_param_value(customer_name_param) + "-" + item['title']
                    if AwsAccount not in titlemsg:
                        titlemsg = titlemsg + "- Account ID :" + AwsAccount
                    agnostic_msg_event_list_json['title'] = titlemsg
                agnostic_msg_event_list_json['longDescription'] = long_description
                if 'category' in item:
                    agnostic_msg_event_list_json['category'] = item['category']
                else:
                    agnostic_msg_event_list_json['category'] = fixed_category
                if 'application' in item:
                    agnostic_msg_event_list_json['application'] = item['application']
                if 'eventsourcecreatedtime' in item:
                    agnostic_msg_event_list_json['eventsourcecreatedtime'] = item['eventsourcecreatedtime']
                if 'incidentCategory' in item:
                    agnostic_msg_event_list_json['incidentCategory'] = item['incidentCategory']
                else:
                    agnostic_msg_event_list_json['incidentCategory'] = fixed_incidentCategory
                if 'incidentSubcategory' in item:
                    agnostic_msg_event_list_json['incidentSubcategory'] = item['incidentSubcategory']
                else:
                    agnostic_msg_event_list_json['incidentSubcategory'] = fixed_incidentSubcategory

                
                # AWSPE-6386: assignment rules will be used to generate the incident with the 
                # correct/desired assignment group since CloudOps is not always the correct team to resolve the issue
                agnostic_msg_event_list_json['foundSupportGroupAction'] = 'UseAssignmentRules'
                
                agnostic_msg_event_list_json['domainName']=get_param_value(domain_name_param)                
                awsaccountname = get_param_value(aws_account_name_param)
                agnostic_msg_event_list_json['node']=getnodeid(item,resourceid)
                businessService = get_param_value(business_service_param)
                #7021,7066 If No resource id is present populating with business service.
                if agnostic_msg_event_list_json['node'] == '' and agnostic_msg_event_list_json['node'] is not None:
                    agnostic_msg_event_list_json['node'] = businessService               
                agnostic_msg_event_list_json['relatedcihints'] = relatedcihints
                 # use account ID if no relatedcihints is provided
                if relatedcihints != '' and relatedcihints is not None:
                    agnostic_msg_event_list_json['relatedcihints'] = relatedcihints 
                else:
                    print('Setting relatedcihints to AWS Account ID')
                    agnostic_msg_event_list_json['relatedcihints'] = businessService
                 
                agnostic_msg_event_list_json['domainLookupBizSrvcName'] = businessService 
                agnostic_msg_event_list_json['custompairs'] = [ 
                    {
                        "name" : "AWSAccountId",
                        "value": AwsAccount,
                    }]
                agnostic_msg_event_list.append(agnostic_msg_event_list_json)
                agnostic_msg = {
                    "EventList": agnostic_msg_event_list
                }

                print("Sending one agnostic_msg: ", agnostic_msg)        
                invoke_send_lambda_response = invoke_send_lambda(agnostic_msg, lambda_send_name, Dlq_Url)
                print("invoke_send_lambda_response is ", invoke_send_lambda_response)

        ### process Alarm message
        else:
            print("Processing Alarm message")
            # Define values
            agnostic_msg = {}
            agnostic_msg_event_list_json = {}
            agnostic_msg_event_list = []
            priority_fields = set_priority(msg)
            print("priority_fields are ", priority_fields)
            severity = priority_fields['severity']
            incidentImpact = priority_fields['incidentImpact']
            event_source_sending_server = get_eventsourcesendingserver(msg)
            event_source_external_id = get_eventsourceexternalid(msg) 
            title = get_alarm_name(msg)
            long_description = get_longdescription(msg)
            application = get_metric_name(msg)
            resourceid = get_resourceid(msg,long_description)
            #node = get_param_value(business_service_param)
            relatedcihints = resourceid
            fixed_category = 'AWS CloudWatch'
            fixed_incidentCategory = 'Hardware'
            fixed_incidentSubcategory = 'Virtual'
            domain_name=get_param_value(domain_name_param)
            # Per ServiceNow team, node and relatedcihints should map to EC2 instnaceId if the instnaceId is present
            #    This will cause the snow logic to look at object_id, correlation_id, and name to try and match.
            
            # Map SNS fields to Agnostic API fields
            agnostic_msg_event_list_json['AWSAccountId'] = AwsAccount
            agnostic_msg_event_list_json['eventsourcesendingserver'] = event_source_sending_server
            agnostic_msg_event_list_json['eventsourceexternalid'] = event_source_external_id
            agnostic_msg_event_list_json['severity'] = severity
            agnostic_msg_event_list_json['incidentImpact'] = incidentImpact
            agnostic_msg_event_list_json['title'] = get_param_value(customer_name_param)+"-"+title
            agnostic_msg_event_list_json['longDescription'] = long_description
            agnostic_msg_event_list_json['category'] = fixed_category
            agnostic_msg_event_list_json['application'] = application
            agnostic_msg_event_list_json['eventsourcecreatedtime'] = event_time
            agnostic_msg_event_list_json['incidentCategory'] = fixed_incidentCategory
            agnostic_msg_event_list_json['incidentSubcategory'] = fixed_incidentSubcategory
            nodevalue = getnodeid(resourceid)
            awsaccountname = get_param_value(aws_account_name_param)
            if nodevalue:
                agnostic_msg_event_list_json['node']=nodevalue
            else:
                agnostic_msg_event_list_json['node']=awsaccountname   

            agnostic_msg_event_list_json['relatedcihints'] = relatedcihints
            agnostic_msg_event_list_json['domainName']=domain_name
            businessService = get_param_value(business_service_param) 
            agnostic_msg_event_list_json['domainLookupBizSrvcName'] = businessService 
            agnostic_msg_event_list_json['custompairs'] = [ 
                {
                    "name" : "AWSAccountId",
                    "value": AwsAccount,
                }]
            agnostic_msg_event_list.append(agnostic_msg_event_list_json)
            agnostic_msg = {
                "EventList": agnostic_msg_event_list
            }
    
            # send the message to the ComSnowSendLambda which will then send to ServiceNow
            print("Sending one agnostic_msg: ", agnostic_msg)        
            invoke_send_lambda_response = invoke_send_lambda(agnostic_msg, lambda_send_name, Dlq_Url)
            print("invoke_send_lambda_response is ", invoke_send_lambda_response)

    except Exception as e:
        print('Error - ',e)

def get_resourceid(msg,longDescription):

    try:
        if 'Trigger' in msg:
            resourceid = msg['Trigger']['Dimensions'][0]['value']
            print("resourceid is ", resourceid)
            return resourceid
        elif 'NewStateReason' in msg:
            new_state_reason = msg['NewStateReason']
        elif longDescription:
            longDescriptiondict = json.loads(longDescription)
            res = longDescriptiondict['EventList'][0]
            if 'NewStateReason' in res:
                new_state_reason = res['NewStateReason']
            else:
                # NewStateReason not found
                return None

        print("new_state_reason is ", new_state_reason)

        if new_state_reason:
            first = '{"' + new_state_reason.split(':')[0].replace(" ","") + '":'
            last = '['+ new_state_reason.split('[')[1] + '}'
            almost_repaired_string = first + " " + last
            repaired_string = almost_repaired_string.replace("'",'"')

            print(repaired_string)
            new_state_reason_dict = json.loads(repaired_string)
            first1 = first.replace('{','')
            first2 = first1.replace('"','')
            first3 = first2.replace(':','')
            thekey = first3
            new_state_reason_list = new_state_reason_dict[thekey]
            # this should return the instnaceid if it is present
            print(new_state_reason_list)
            resourceid = new_state_reason_list[0]['ResourceId']
            print("resourceid is ", resourceid)
            return resourceid
            
        else:
            # NewStateReason not found
            return None
    except Exception as e:
        print('Error in get_resourceid - ',e)

def get_alarm_name(msg):
    try:
        if 'AlarmName' in msg:
            alarm_name = msg['AlarmName']
        else:
            alarm_name = 'No AlarmName Provided'
        return alarm_name

    except Exception as e:
        print('Error setting long description - ',e)
       
 
def get_metric_name(msg):
    try:
        if 'MetricName' in msg['Trigger']:
            metric_name = msg['Trigger']['MetricName']
        else:
            metric_name = 'No MetricName Provided'
        return metric_name

    except Exception as e:
        print('Error setting long description - ',e)


def get_longdescription(msg):
    try:
        long_description = json.dumps(msg, sort_keys=True, indent=2, separators=(',', ': '))
        return long_description

    except Exception as e:
        print('Error setting long description - ',e)


def get_eventsourceexternalid(msg):
    # use the AWS Account Id from the message if it exists, otherwise, use accountID from the stack
    try:
        if 'AWSAccountId' in msg:
            eventsourceexternalid = 'Account: ' + msg['AWSAccountId'] + ', Region: ' + AwsRegion
        else:
            eventsourceexternalid = 'Account: ' + AwsAccount + ', Region: ' + AwsRegion
        print("eventsourceexternalid is ", eventsourceexternalid)
        return eventsourceexternalid
    except Exception as e:
        print('Error setting event source external id - ',e)


def get_eventsourcesendingserver(msg):
    try:
        print("inside get_eventsourcesendingserver")
        if 'Dimensions' in msg['Trigger']:
            dim_list = msg['Trigger']['Dimensions']
            for item in dim_list:
                if 'name' in item.keys() and 'value' in item.keys() and 'InstanceId' in item.values():
                    eventsourcesendingserver = item['value']
                    print("Using InstanceId from Trigger for eventsourcesendingserver: ", eventsourcesendingserver)
        elif 'InstanceId' in msg:
            eventsourcesendingserver = msg['InstanceId']
            print("Using InstanceId for eventsourcesendingserver: ", eventsourcesendingserver)
        elif 'AWSAccountId' in msg:
            eventsourcesendingserver = msg['AWSAccountId']
            print("InstanceId not found, using Account ID")
        else:
            print("InstanceId and account ID not found, using local account ID")
            eventsourcesendingserver = AwsAccount
        return eventsourcesendingserver
    except Exception as e:
        print('Error setting event source sending server - ',e)


def set_priority(msg):
    # severity and incidentImpact will be set according to the PriorityData json field sent to the SNS topic
    # If no PriorityData json field is sent, then priority will be determined by the severity and incidentImpact fileds, if present.
    # if neither of these are provided, the fields will be set for priority 3
    try:
        print("msg in set_priority is ", msg)
        priority_fields = {
                          "severity": None,
                          "incidentImpact": None
                        }
        # SNS topic input
        if 'PriorityData' in msg:
            print("SNS topic PriorityData is ", msg['PriorityData'])
            PriorityValue = msg['PriorityData']['Priority']
            if PriorityValue == "1":
                priority_fields['severity'] = "Critical"
                priority_fields['incidentImpact'] = "1"
            elif PriorityValue == "2":
                priority_fields['severity'] = "Major"
                priority_fields['incidentImpact'] = "2"
            elif PriorityValue == "3":
                priority_fields['severity'] = "Minor"
                priority_fields['incidentImpact'] = "3"
            elif PriorityValue == "4":
                priority_fields['severity'] = "Warning"
                priority_fields['incidentImpact'] = "4"
            else:
                priority_fields['severity'] = "Minor"
                priority_fields['incidentImpact'] = "3"
        # Agnostic API input
        elif 'PriorityData' in msg['EventList'][0]:
            print("Agnostic API PriorityData is ", msg['EventList'][0])
            PriorityValue = msg['EventList'][0]['PriorityData']['Priority']
            if PriorityValue == "1":
                priority_fields['severity'] = "Critical"
                priority_fields['incidentImpact'] = "1"
            elif PriorityValue == "2":
                priority_fields['severity'] = "Major"
                priority_fields['incidentImpact'] = "2"
            elif PriorityValue == "3":
                priority_fields['severity'] = "Minor"
                priority_fields['incidentImpact'] = "3"
            elif PriorityValue == "4":
                priority_fields['severity'] = "Warning"
                priority_fields['incidentImpact'] = "4"
            else:
                priority_fields['severity'] = "Minor"
                priority_fields['incidentImpact'] = "3"

        # PriorityData not provided in input, check for severity and incidentImpact
        elif ('severity' in msg['EventList'][0]) and ('incidentImpact' in msg['EventList'][0]):
            print("using severity and incidentImpact from the input message")
            priority_fields['severity'] = msg['EventList'][0]['severity']
            priority_fields['incidentImpact'] = msg['EventList'][0]['incidentImpact']
            
        else:
            print("PriorityData does not exist in inputfile, setting priority to 3")
            priority_fields['severity'] = "Minor"
            priority_fields['incidentImpact'] = "3"
        return priority_fields

    except Exception as e:
        print('Error, invalid JSON - ',e)
        priority_fields['severity'] = "Minor"
        priority_fields['incidentImpact'] = "3"
        return priority_fields

        
def invoke_send_lambda(msg, lambda_send_name, Dlq_Url):
    try:
        print("msg in invoke_send_lambda is ", msg)
        print("lambda_send_name in invoke_send_lambda is", lambda_send_name)
        invoke_response = lambda_client.invoke(
                              FunctionName=lambda_send_name,
                              InvocationType='Event',
                              #Payload=b'bytes'|file,
                              Payload=json.dumps(msg)
                          )
        print("invoke_response is ", invoke_response)
        return invoke_response
    except Exception as e:
        print("Error in invoke_send_lambda - ", e)
        send_to_dlq(msg, Dlq_Url)


def send_to_dlq(msg, Dlq_Url):
    msg_string = json.dumps(msg)
    try:
        sqs_response = sqs_client.send_message(
                QueueUrl=Dlq_Url,
                MessageBody=msg_string
            )
    except Exception as e:
        print("Error in send_to_dlq - ", e)

def get_param_value(param):
    try:
        response = ssm_client.get_parameter(Name=param)
        return response['Parameter']['Value']
    except Exception as e:
        print("Error-get_param_value()",e)
        
def getnodeid(item={},resourceid=''):
    """
    """
    node = ''
    if 'node' in item:
        print("Node", item['node'])
        node = item['node']
    else:
        if resourceid:
            print("resourceid :", resourceid)
            node = resourceid
    return node
    

def lambda_handler(event, context):
    try:
        print('Snow Parser Event Received - ',event)
        print('Snow Parser Context Received - ',context)
        event_record = event['Records']
        print("event_record is ", event_record)
        lambda_send_name = 'ComSnowSendLambda-'+AwsRegion
        body = event['Records'][0]['body']
        body_dict = json.loads(body)
        event_time = body_dict['Timestamp']
        
        for record in event_record:
            record_body_dict = json.loads(record['body'])
            record_msg_dict = json.loads(record_body_dict['Message'])
            format_agnostic_msg(record_msg_dict, lambda_send_name, event_time, Dlq_Url)
    except Exception as e:
        print('Error in lambda_handler - ',e)
