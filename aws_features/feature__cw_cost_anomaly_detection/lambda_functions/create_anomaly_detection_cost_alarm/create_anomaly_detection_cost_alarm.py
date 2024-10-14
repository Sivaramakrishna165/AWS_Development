"""
It compares the cost-anomaly detection history with DynamoDB data and sends the notification to the cloudops then it 
creates the incidents in service now. It doesn't require any input to trigger
"""
import boto3
from botocore.config import Config
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import uuid
import json
import traceback
import os
from datetime import datetime, timedelta

config=Config(retries=dict(max_attempts=10,mode='standard'))

dynamodb = boto3.resource('dynamodb',config=config)
dynamodb_client = boto3.client('dynamodb',config=config)
ce_clinet = boto3.client('ce',config=config)
ses_client = boto3.client('ses',config=config)
sns_client = boto3.client('sns',config=config)

topic_arn = os.environ['SNS_TOPIC']
Notify_cloud_ops = os.environ['CloudOpsEmail_ids']
sender = os.environ['sender']
table_name = os.environ['table_name']

current_date = datetime.now()

def read_incident_priority(feature_name):
    error = False
    try:

        account_definition_reponse = dynamodb_client.get_item(
            TableName='AccountFeatureDefinitions',
            Key={'Feature': {'S': feature_name}}
        )

        incident_priority =  account_definition_reponse['Item']['FeatureParams']['M']['pfSnowInciPriority']['M']['Default']['S']
        print(f"Incident Priority is: {incident_priority}")

        if (incident_priority in ["1","2","3"]):
            pass
        else:
            print(f"Incident Priority '{incident_priority}' does not match expected values ('1','2' or '3'). Taking fallback value: '3'.")
            

        return incident_priority, error

    except Exception as e:
        print(f"Error reading dynamodb table 'AccountFeatureDefinitions' with key 'Feature':{feature_name}")
        print(f"Taking fallback incident priority = '3'.")
        incident_priority = "3"
        return incident_priority, error

def read_ssm_parameter(name):
    ssm_para_client = boto3.client('ssm',config=config)
    response = ssm_para_client.get_parameter(
        Name=name,
    )
    ssm_parameter = response['Parameter']
    ssm_parameter_value = ssm_parameter['Value']
    return ssm_parameter_value

def event_key():
    key = str(uuid.uuid1())
    return key

def send_to_FtCommonServiceNow(API_message):
    except_reason = None
    try:
        print('API message is :', API_message)
        sns_client_response = sns_client.publish(
            MessageStructure='json',
            Message=json.dumps(
                        {'default': json.dumps(API_message)}
                    ),
            TopicArn=topic_arn
        )
        print("sns_client_response is: ", sns_client_response)
    except Exception as e:
        print('Error:send_to_FtCommonServiceNow()-', e)
        except_reason = 'Error in send_to_FtCommonServiceNow' + str(traceback.format_exc()) 
    if except_reason is not None:
        return except_reason
    else:
        return 'SUCCESS'     

def EventBody(event,Request_id,account_id,Long_description):
    body = {}
    error = False
    try:
        
        short_description = "AWSPlatformEngineering-AWS 338395754338 | Cost Anomaly Detection Incident On "+str(current_date)
        description = Long_description
        
        account_id = account_id
        
        key=event_key()
        
        severity_dict = { "1":"Critical", "2":"Major", "3":"Minor", "4":"Warning"}
        new_state_reason = 'AWS Cost Anomaly solution: ' + str([{'Notification':'false'}])
        priority,error = read_incident_priority("CWCostAnomalyDetection")
        Severity = severity_dict[priority]
        body = {
                "EventList":[
                    {
                    "AWSAccountId":account_id,
                    "NewStateReason": new_state_reason,
                    "eventsourcesendingserver":"AWS CostAnomlay",
                    "eventsourceexternalid":Request_id,
                    "severity":Severity,
                    "title":short_description,
                    "longDescription":description,
                    "category":"AWS CloudWatch",
                    "key":key,
                    "domainName":"CSC-I",
                    "application": "feature__Anomaly_detection",
                    "eventsourcecreatedtime": str(current_date),
                    "PriorityData" : {
                        "Priority": priority
                    }    
                    }
                    ]
                }
                
        print("EventBody returned")
    except Exception as e:
        print("Error EventBody() - ", e)
        error = traceback.format_exc()
    finally:
        return body,error


def send_mail(html,start,end,AccountName,account_id):
    try:
        print("send_mail triggered.")
        
        SENDER = read_ssm_parameter(sender)
        
        print("Sender's email_is : ", SENDER)
        CloudOpsTeamEmail_ids = read_ssm_parameter(Notify_cloud_ops)
        print("CloudOpsTeamEmail_ids : ",CloudOpsTeamEmail_ids)
        
        value = CloudOpsTeamEmail_ids
        recipientMailIDs = []
        rejected_mails = []
        for toMailId in value.split(";"):
            if toMailId != "":
                recipientMailIDs.append(toMailId)
        print("\nTo Mail ID : ", recipientMailIDs)
        response = ses_client.get_identity_verification_attributes(
            Identities=recipientMailIDs
        )
        for i in recipientMailIDs:
            if i in response['VerificationAttributes'].keys():
                if response['VerificationAttributes'][i]['VerificationStatus'] == 'Success':
                    continue
            rejected_mails.append(i)
                    
        print("emails not verified: " + str(rejected_mails))

        recipient_mails = list(set(recipientMailIDs) - set(rejected_mails))
        print("verified emails: " + str(recipient_mails))

        msg = MIMEMultipart('mixed')
        msg['Subject'] = "AWS Cost Management: Cost anomalies summary for account: "+AccountName+" ("+account_id+") ["+start+" to "+end+"}]"
        msg['From'] = SENDER
        msg['To'] = ','.join(recipient_mails)

        msg_body = MIMEMultipart("alternative", None, [MIMEText(html,'html')])
        msg.attach(msg_body)

        response = ses_client.send_raw_email(
            Source=SENDER,
            Destinations=recipient_mails,
            RawMessage={
                'Data': msg.as_string()
            },
        )
        print("email sent.")
    except Exception as e:
        print("Error send_mail() - ",e)

def create_html_body(cost_total_impact,cost_service,cost_usage_type,cost_Region,yesterday,today,AccountName,account_id):
    try:
        print("html_body triggered.")
        i=0
        
        table = "<table>"
        table = table + "<tr><td>Service</td><td>Start Date</td><td>Last Detected Date</td><td>Cost Impact</td><td>Root Cause(s)</td><td>Monitor</td></tr>"
        for service in cost_service:
            table = table + "<tr><td>"+service+"</td><td>"+yesterday[i]+"</td><td>"+today[i]+"</td><td>Total Impact : "+cost_total_impact[i]+"</td><td>Region : "+cost_Region[i]+" And Usage Type : "+cost_usage_type[i]+"</td><td>cost-anomaly</td></tr>"
            i=i+1
        table = table + "</table>"

        html = """
        <html>
        <head>
        <style> 
        table, th, td {{ border: 2px solid black; }}
        th, td {{ border: 1.5px solid black; background-color: #f0f0f0; }}
        </style>
        </head>
        <body><p>AWS Cost Management: Anomaly Detection<br>
        AWS Account: {AccountName} ({account_id})</p>
        <p>Dear AWS Customer, </p>
        <p>You are receiving this alert because you asked us to provide you with a summary of unusual AWS usage patterns for accounts in your AWS organization with payer account id number above. Below is a recent list of anomalies that have been detected up until
        today with corresponding root cause(s).</p>
        <p>{table}</p>
        <p>If you have any questions regarding the information in this email or if you need additional assistance, please contact us at<br>
        https://aws.amazon.com/support.</p>
        </body></html>
        """
        html = html.format(account_id = account_id,AccountName = AccountName,table = table)
        
        
    except Exception as e:
        error_status = True 
        html=''
        print("Error html_body() - ",e)
    return html

def lambda_handler(event, context):
    try:
        print('Received event is ',event)
        AccountName = boto3.client('iam',config=config).list_account_aliases()['AccountAliases'][0]
        account_id = boto3.client("sts").get_caller_identity()["Account"]
        
        table = dynamodb.Table(table_name)
        response = table.scan()
        data = response['Items']
        print(data)
        day = current_date - timedelta(days=0)
        end_date = str(day.strftime("%Y-%m-%d"))
        day = current_date - timedelta(days=6)
        start_date = str(day.strftime("%Y-%m-%d"))
        
        print("start date is ",start_date," and end date is ",end_date)
        AnomalyStartDate =''
        AnomalyEndDate = ''         
        response = ce_clinet.get_anomaly_monitors()
        for anomaly in response['AnomalyMonitors']:
            if anomaly['MonitorName'] == 'cost-anomaly-detection':
                monitor_arn = anomaly['MonitorArn']
                cost_service=[]
                cost_total_impact=[]
                cost_usage_type = []
                cost_Region= []
                AnomalyStartDate = []
                AnomalyEndDate = []
                
                response = ce_clinet.get_anomalies(
                    MonitorArn=monitor_arn,
                    DateInterval={
                        'StartDate': start_date
                    }
                )
                
                for anomalies in response['Anomalies']:
                    AnomalyStartDate.append(anomalies['AnomalyStartDate'])
                    
                    AnomalyEndDate.append(anomalies['AnomalyEndDate'])
                    
                    for cause in anomalies['RootCauses']:
                        service_name = cause['Service']
                        
                        try:
                            UsageType = cause['UsageType']
                        except Exception as e:
                            UsageType = 'Not found'
                            print(f"No usage for {service_name} service")
                        try:
                            Region = cause['Region']
                        except Exception as e:
                            Region = 'Not found'
                            print(f"Region not found for {service_name} service")
                        
                        total_impact=float(anomalies['Impact']['TotalImpact'])
                        for item in data:
                            if item['ServiceName'] == service_name:
                                print("Matched service is",item['ServiceName'])
                                if total_impact >= float(item['CostImpact']):
                                    print("Matched cost impact is ",item['CostImpact'])
                                    
                                    cost_total_impact.append(str(total_impact))
                                    cost_service.append(service_name)
                                    cost_usage_type.append(UsageType)
                                    cost_Region.append(Region)    
                if cost_service != []:
                    html=create_html_body(cost_total_impact,cost_service,cost_usage_type,cost_Region,AnomalyStartDate,AnomalyEndDate,AccountName,account_id)
                    send_mail(html,start_date,end_date,AccountName,account_id)
                    try:
                        Request_id = context.aws_request_id
                        Long_description = { "Services":cost_service, "Start Date":AnomalyStartDate, "Last Detected Date":AnomalyEndDate, "Cost Impact":cost_total_impact,"Root Cause(s)":cost_usage_type,"Monitor":"cost-anomaly"}
                        API_message, error = EventBody(event,Request_id,account_id,Long_description)
                        if error:
                            raise Exception("Error while forming api message body. Please check payload passed. snow incident not created")
                        
                        event_status = send_to_FtCommonServiceNow(API_message)
                        if event_status != "SUCCESS":
                            raise Exception("Error while creating incident/event. SNow Incident not created.")
                        event["Event_status"] = event_status
                        
                    except Exception as e:
                        print("Error lambda_handler() - ", e)
                        input = {"error": e}
                        if not error:
                            error = traceback.format_exc()
                    
    except Exception as e:
        print("Error lambda_handler() - ",e)