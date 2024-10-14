import boto3
import re
from botocore.config import Config
from botocore.exceptions import ClientError
from datetime import datetime
import io
import csv
import os
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))

s3_bucket = os.environ['target_S3_bucket_parameter']
customer_name = os.environ['customer_name_parameter']
ssmclient = boto3.client('ssm',config=config)

def lense(milestone_lenses,alias,share,latest,owner,workloadARN,Account_ID,HIGH_Risk,MEDIUM_Risk,k,l,client,Region,workloadid,workloadname,writer,writer_2,name,owner_emil_ids):
    try:
        now = datetime.now()
        print("now =", now)
        dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
        
        for lensid in range(len(milestone_lenses['LensReviewSummaries'])):
            if 'LensArn' in milestone_lenses['LensReviewSummaries'][lensid].keys():
                lens=milestone_lenses['LensReviewSummaries'][lensid]['LensArn']
            else:
                lens=milestone_lenses['LensReviewSummaries'][lensid]['LensAlias']

            lense_review=client.get_lens_review(
            WorkloadId=workloadid,
            LensAlias=lens
            )

            list_pillars=lense_review['LensReview']['PillarReviewSummaries']
            
            for pillars in list_pillars:
                pillar = pillars['PillarId']

                answers=client.list_answers(
                WorkloadId=workloadid,
                PillarId=pillar,
                LensAlias=lens,
                MaxResults=20)
            
                for i in range(len(answers["AnswerSummaries"])):
                    questionid=answers["AnswerSummaries"][i]["QuestionId"]

                    answer=client.get_answer(
                        WorkloadId=workloadid,
                        LensAlias=lens,
                        QuestionId=questionid
                        )

                    questiontitle=answers["AnswerSummaries"][i]["QuestionTitle"]
                    questiontitle=questiontitle.encode('ascii', 'ignore').decode('ascii')
                    questiontitle=questiontitle.strip()
                    risk_answer=answer["Answer"]["Risk"]
                    if risk_answer == 'HIGH':
                        HIGH_Risk = HIGH_Risk + 1
                    elif risk_answer == 'MEDIUM':
                        MEDIUM_Risk = MEDIUM_Risk + 1
                    for choice in range(len(answer["Answer"]["Choices"])):
                        choiceid=answer["Answer"]["Choices"][choice]['ChoiceId']
                        choicetitle=answer["Answer"]["Choices"][choice]["Title"]
                        choicetitle=choicetitle.encode('ascii', 'ignore').decode('ascii')
                        choicetitle=choicetitle.strip().replace("\n", " ")
                        choicetitle=re.sub(' +',' ',choicetitle)
                        choicetick=""
                        choicereason=""
                        choicereasonnotes=""
                        if answer["Answer"]["Choices"][choice]["ChoiceId"] in answer["Answer"]["SelectedChoices"]:
                            choicetick="X"
                        for choiceanswer in  range(len(answer["Answer"]["ChoiceAnswers"])):
                            if answer["Answer"]["Choices"][choice]["ChoiceId"] == answer["Answer"]["ChoiceAnswers"][choiceanswer]["ChoiceId"]:
                                if answer["Answer"]["ChoiceAnswers"][choiceanswer]["Status"] ==  "NOT_APPLICABLE":
                                    choicetick="NA"
                                    choicereason=answer["Answer"]["ChoiceAnswers"][choiceanswer]["Reason"]
                                    choicereasonnotes=answer["Answer"]["ChoiceAnswers"][choiceanswer]["Notes"]
                        
                       
                        l = l + 1
                        writer.writerow(
                            [l,
                            name,
                            alias,
                            owner,
                            Account_ID,
                            workloadname,
                            workloadid,
                            workloadARN,
                            risk_answer,
                            Region,
                            lens,
                            pillar,
                            questiontitle,
                            choicetitle,
                            choicetick,
                            choicereason,
                            choicereasonnotes,
                            share,
                            latest,
                            dt_string
                            ])
                        
        print("last High risk is ",HIGH_Risk)
        print("last Medium risk is ",MEDIUM_Risk)

        writer_2.writerow([
            name,
            alias,
            workloadname,
            workloadid,
            owner,
            Account_ID,
            Region,
            HIGH_Risk,
            latest,
            dt_string
        ])
        # high_risk_workload.append(HIGH_Risk)
        # if len(high_risk_workload) <=1:
        #     workload_High_risks.append(HIGH_Risk)
        # else:
        # workload_High_risks.append(high_risk_workload)
        # workload_High_risks.append(HIGH_Risk)
        owner_emil_ids.append(owner)
    except Exception as e:
        print("Error in lenses() ",e)
    return k,l,HIGH_Risk,owner_emil_ids

def list_workload(k,l,Region,my_config,regions_names,workload_names,writer,writer_2,name,workload_High_risks,owner_emil_ids):
    try:
        client = boto3.client('wellarchitected',config=my_config)
        listworkloads = client.list_workloads()
        region_workload = []
        high_risk_workload = []
        for id in range(len(listworkloads["WorkloadSummaries"])):
            HIGH_Risk = 0
            MEDIUM_Risk = 0
            count=0
            alias = boto3.client('iam').list_account_aliases()['AccountAliases'][0]
            workloadid=listworkloads["WorkloadSummaries"][id]["WorkloadId"]
            workloadname=listworkloads["WorkloadSummaries"][id]["WorkloadName"]
            print("workload name is ",workloadname)
            workloadARN = listworkloads["WorkloadSummaries"][id]["WorkloadArn"]
            Account_ID = listworkloads["WorkloadSummaries"][id]["Owner"]
            latest = 'Updated at ' + str(listworkloads["WorkloadSummaries"][id]["UpdatedAt"])
            share=""
            owner=""
            try:
                workload_share = client.list_workload_shares(
                    WorkloadId = workloadid
                )
                for shares in workload_share['WorkloadShareSummaries']:
                    share = shares['ShareId']
                    break
            except Exception as e:
                print("There is no workload_share ",e)
            try:
                owner_response = client.get_workload(
                    WorkloadId = workloadid
                )
                owner = owner_response['Workload']['ReviewOwner']
            except Exception as e:
                print("There is no owner owner_reponse ",e)
            
            print("owner is : ",owner)
            milestones = client.list_milestones(
                WorkloadId = workloadid
            )
            print("length is : ",len(milestones['MilestoneSummaries']))
            # if len(milestones['MilestoneSummaries']) == 0:
            print("milestone is none")
            milestone_lenses=client.list_lens_reviews(
                WorkloadId=workloadid
            )
            print("After lenses")
            
            k=k+1   
            
            region_workload.append(workloadname)
            k,l,High_risk,owner_emil_ids = lense(milestone_lenses,alias,share,latest,owner,workloadARN,Account_ID,HIGH_Risk,MEDIUM_Risk,k,l,client,Region,workloadid,workloadname,writer,writer_2,name,owner_emil_ids)
            high_risk_workload.append(High_risk)
        if len(region_workload) <=1:
            workload_names.append(workloadname)
        else:
            workload_names.append(region_workload)
        if len(high_risk_workload)<=1:
            workload_High_risks.append(High_risk)
        else:
            workload_High_risks.append(high_risk_workload)
        regions_names.append(Region)
    except Exception as e:
        print("Unable to process the workload in this region in list_workload() ",e)
    return regions_names,workload_names,k,l,workload_High_risks,owner_emil_ids                

def regions(regions_names,workload_names,writer,writer_2,name,workload_High_risks,owner_emil_ids):
    try:
        ec2 = boto3.client('ec2')
        regions = ec2.describe_regions()
        l=0
        k=0
        for num in range(len(regions['Regions'])):
            Region = regions['Regions'][num]['RegionName']
            print("Region is : ",Region)

            my_config = Config(
                    region_name = Region
                    )
            regions_names,workload_names,k,l,workload_High_risks,owner_emil_ids = list_workload(k,l,Region,my_config,regions_names,workload_names,writer,writer_2,name,workload_High_risks,owner_emil_ids)
    except Exception as e:
        print("This region is not having the aws services",e)
    return regions_names,workload_names,workload_High_risks,owner_emil_ids

def get_ssm_paramter(s3_bucket):
    try:
        value = ""
        response = ssmclient.get_parameter(
            Name=s3_bucket
        )
        value = response['Parameter']['Value']
    except Exception as e:
        value = ""
        print("unable to cont ..",e)
    return value

def lambda_handler(event, context):

    name = ''
    writer = ''
    writer_2 =''
    regions_names = []
    workload_names = []
    workload_High_risks = []
    owner_emil_ids = []
    bucket_name = get_ssm_paramter(s3_bucket)
    name = get_ssm_paramter(customer_name)
    # bucket = bucket_name
    print('received event is ',event)
    
    timestr = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S:%f')

    account_id = boto3.client("sts").get_caller_identity()["Account"]

    s3_client = boto3.client('s3')

    csvio = io.StringIO()
    csvoo = io.StringIO()
    writer = csv.writer(csvio)
    writer_2 = csv.writer(csvoo)

    writer.writerow(['Sl No',
    'Customer Name',
    'Account Name',
    'Owner Name',
    'Account ID',
    'Workload Name',
    'Workload Id',
    'Workload ARN',
    'Risk',
    'Region',
    'Lens',
    'Pillar',
    'Question Title',
    'Choice Title',
    'Choice Selected',
    'Choice Reason',
    'Choicereasonnotes',
    'Latest ShareID',
    'Last Update',
    'Report Timestamp'
    ])
    writer_2.writerow([
        'Customer Name',
        'Account Name',
        'Workload Name',
        'Workload Id',
        'Owner Name',
        'Account ID',
        'Region',
        'Identified HIGH Risk',
        'Last Update date',
        'Report Timestamp'
    ]
    )

    file = "war_report_data"+"/"+"war_report_"+account_id +"/"+timestr+'_war_report_'+ '.csv'

    file_2="war_report_summary"+"/"+"war_summary_"+account_id+"/"+timestr+'_war_report_summary_'+ '.csv'
    
    regions_names,workload_names,workload_High_risks,owner_emil_ids = regions(regions_names,workload_names,writer,writer_2,name,workload_High_risks,owner_emil_ids)
    
    if bucket_name != "":
        s3_client.put_object(Body=csvio.getvalue(), ContentType='application/vnd.ms-excel', Bucket=bucket_name, Key=file)
        csvio.close()

        print("WAR Report File path is " + file  + " uploaded to S3 s3://" + bucket_name)

        s3_client.put_object(Body=csvoo.getvalue(), ContentType='application/vnd.ms-excel', Bucket=bucket_name, Key=file_2)
        csvoo.close()

        print("WAR Summary File path is " + file_2  + " uploaded to S3 s3://" + bucket_name)
    else:
        print("bucket name is empty")
    event = {}
    event['Regions'] = regions_names
    event['Workloads'] = workload_names
    event['HighRisks']=workload_High_risks
    event['owners'] = owner_emil_ids
        
    return event

