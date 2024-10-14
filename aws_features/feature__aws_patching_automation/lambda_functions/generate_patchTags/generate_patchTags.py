'''
This Lambda script generates the PatchInstallOn tag on the eligible instance to schedule and patch
'''

import boto3
import os
import sys
import time
import calendar
import datetime
from dateutil import relativedelta
import json
import uuid
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))

def generate_uniqueId():
    patchJobId = "patchJobId_" + str(uuid.uuid1())
    return patchJobId

def PrintException():
    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    captureErr = "Line No. : " + str(lineno)  + " | ERROR: " + str(exc_obj)
    return captureErr
    

def find_patchWindow_for_Server(ec2,instance,day,week,month,hour,Year,minute,duration,nextmonthInt,nextmonthStr,ord_No,patchStartDate,patchEndDate,selectDowntimeForPatchGroup,nextPatchGroupStartDate,downtimeFoundForImmediateNextMonth,patchGroup):
    try:
        ec2_client = boto3.client('ec2',region_name = region,config=config)
        dayOnNumber = {"MON": 0 ,"TUE": 1, "WED": 2, "THU": 3, "FRI": 4, "SAT": 5, "SUN": 6 }
        downtimeDay = None
        patchInstallOnStr = ""

        print("Value of month passed to 'find_patchWindow_for_Server' : ",month , " - Type : ", type(month))
        downtimeMonth = None
        if month == "*":
            downtimeMonth = nextmonthInt
            patchInstallOnStr += nextmonthStr + "_"
        elif nextmonthStr in month:
            downtimeMonth = nextmonthInt
            patchInstallOnStr += nextmonthStr + "_"  
        if downtimeMonth == None:
            return None,False
        #print("DOWNTIME MONTH =======> ", downtimeMonth)                        
        j = 1
        print("\nDay : ",day )
        print("Week : ",week )
        for weeks in calendar.monthcalendar(int(Year), int(nextmonthInt)):
            #print("\nWEEKS : ",weeks)
            if week != "*":
                if j == 1:
                    print("In First week : " , weeks[dayOnNumber[day]])
                    if weeks[dayOnNumber[day]] == 0:
                        print("First week of day is 0. So incrementing week to get correct day")
                        week = int(week) + 1
                if int(week) == j:
                    downtimeDay = weeks[dayOnNumber[day]]
                    print("downtimeDay[if block] : ",downtimeDay, " | value of j : ",j)
            else:
                downtimeDay = weeks[dayOnNumber[day]]
                print("downtimeDay[else block] : ",downtimeDay)
                                        
            if downtimeDay != None and downtimeDay != 0:
                #print("downtimeDay = ",downtimeDay , "downtimeMonth = ", downtimeMonth , "Year : ",Year)
                downtimeDate_str = str(downtimeDay) + "-" +  str(downtimeMonth) + "-" + str(Year)
                downtimeDate = datetime.datetime.strptime(downtimeDate_str, '%d-%m-%Y')
                print("\ndowntimeDate : ",downtimeDate)
                print("patchStartDate : ", patchStartDate)
                print("patchEndDate : ", patchEndDate)
                #print("Ord_No : ",ord_No)
                #print("nextPatchGroupStartDate : ",nextPatchGroupStartDate)
                #if ord_No > 1 and nextPatchGroupStartDate != None:
                #    patchStartDate = nextPatchGroupStartDate + datetime.timedelta(days=int(patchOrderInfo['waitDaysBetweenGroups']))
                    #print("Next Patch Group Start Date : ",patchStartDate)
                if downtimeDate >= patchStartDate and downtimeDate < patchEndDate:
                    downtimeFoundForImmediateNextMonth = True
                    print("Downtime condition meets with Start & End Monthly Patch date")
                    patchInstallOnStr += str(downtimeDay) + "_" + str(Year) + "_" + str(hour) + "_" + str(minute) + "_" + str(duration) + "HRS"
                    patchInstallOnStr = patchGroup + '-' + patchInstallOnStr
                    print("Patch InstallOn Str : ", patchInstallOnStr)
                    try:
                        count=0
                        for tag in ec2.tags:
                            if tag["Key"] == patchinstalltag:
                                if tag['Value'] == patchInstallOnStr:
                                    print("Patch Install tag is present ",instance)
                                else:
                                    count = 1
                                    print("Patch Install tag is present but not same ",instance)
                                    response = ec2_client.create_tags(
                                        Resources=[
                                            instance,
                                        ],
                                        Tags=[
                                            {
                                                'Key': temppatchinstalltag,
                                                'Value': patchInstallOnStr
                                            },
                                        ]
                                    )
                        if count != 1:
                            print("Patch Install tag is not present ",instance)
                            response = ec2_client.create_tags(
                                        Resources=[
                                            instance,
                                        ],
                                        Tags=[
                                            {
                                                'Key': patchinstalltag,
                                                'Value': patchInstallOnStr
                                            },
                                        ]
                                    )
                        selectDowntimeForPatchGroup.append(downtimeDate)
                        #selectDowntimeForPatchGroup.sort(reverse=True)
                        nextPatchGroupStartDate = max(selectDowntimeForPatchGroup)
                        if patchInstallOnStr not in patchInstallOnValue:
                                patchInstallOnValue.append(patchInstallOnStr)
                    except:
                        print(PrintException())
                    break    
            j = j+1
        return nextPatchGroupStartDate,downtimeFoundForImmediateNextMonth
    except:
        print(PrintException())


def generate_patchTags(TagName,S3_Bucket,osPlatform):
    try:
        ec2_client = boto3.client('ec2',region_name = region,config=config)
        ec2_resource = boto3.resource('ec2',region_name = region)

        patchInstallOnStr = ""
        monthsList = []
        
        #nextmonth = datetime.date.today() + relativedelta.relativedelta(months=1)

        # Modified solution to run CW rule to schedule patching for Current Month (Previously it was for next month). Hence, finding current month instead of next month.
        # But have not changed the variable "nextmonth". Just keep using the same variable even it is for current month as it is difficult now to change the variable name
        nextmonth = datetime.date.today() + relativedelta.relativedelta(months=0)
        
        Year = nextmonth.strftime("%Y")
        S3_directory_year = nextmonth.strftime("%Y")
        nextmonth = nextmonth.strftime("%b-%m")
        #print("Next Month : ", nextmonth)
        print("Current Month : ", nextmonth)
        nextmonthStr = nextmonth.split("-")[0]
        nextmonthStr = nextmonthStr.upper()
        nextmonthInt = nextmonth.split("-")[1]
        
        #nextToNextMonth = datetime.date.today() + relativedelta.relativedelta(months=2)
        nextToNextMonth = datetime.date.today() + relativedelta.relativedelta(months=1)
        
        nextToNextMonth_Year = nextToNextMonth.strftime("%Y")
        nextToNextMonth = nextToNextMonth.strftime("%b-%m")
        #print("Next To Next Month : ", nextToNextMonth)
        print("Next Month : ", nextToNextMonth)
        nextToNextMonthStr = nextToNextMonth.split("-")[0]
        nextToNextMonthStr = nextToNextMonthStr.upper()
        nextToNextMonthInt = nextToNextMonth.split("-")[1]
        
        
        dayOnNumber = {"MON": 0 ,"TUE": 1, "WED": 2, "THU": 3, "FRI": 4, "SAT": 5, "SUN": 6 }
        nextPatchGroupStartDate = None
        
        monthOnNumber = {"JAN": 1 ,"FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6, "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12 }
        
        # Finding Start and End date for Monthly Patching
        patchingOccurrence = osPlatform + "PatchingOccurrence"
        patchDay = None
        endDay = None
        daysToAdd = 0
        if patchOrderInfo[patchingOccurrence] == "MONTHLY":
            print("PATCH TYPE : MONTHLY")
            #Finding Monthly Start Date of Patching from Input of JSON(SSM parameter)
            weekToStartMontlyPatching = "weekToStartMontlyPatching_" + osPlatform
            weekToStartMonthly = patchOrderInfo[weekToStartMontlyPatching]
            day = weekToStartMonthly.split("_")[2]
            week_monthly = weekToStartMonthly.split("_")[1]
            
            i = 1
            week = week_monthly
            print(f"Year : {Year} | nextmonthInt : {nextmonthInt}")
            for weeks in calendar.monthcalendar(int(Year), int(nextmonthInt)):
                if i == 1:
                    tempDayValue = weeks[dayOnNumber[day]]
                    if int(week) > 1 and tempDayValue == 0:
                        week = int(week) + 1
                if int(week) == i:
                    patchDay = weeks[dayOnNumber[day]]
                if patchDay == 0:
                    patchDay = weeks[dayOnNumber[day]]
                i = i+1
            patchStartDate_str = str(patchDay) + "-" +  str(nextmonthInt) + "-" + str(Year)
            patchStartDate = datetime.datetime.strptime(patchStartDate_str, '%d-%m-%Y')
            if "+" in weekToStartMonthly:
                daysToAdd = weekToStartMonthly.split("_")[4]
                if int(daysToAdd) > 7:
                    print(f"Day To Add on weekToStartMonthly is GREATER THAN 7. Qutting execution....")
                    sys.exit(1)
                else:
                    patchStartDate = patchStartDate + datetime.timedelta(days=int(daysToAdd))
            print("Monthly Patch Start Date : ", patchStartDate)
            
            #Finding Monthly End Date of Patching
            i = 1
            week = week_monthly
            if int(nextmonthInt) == 12:
                EndYear = int(Year) + 1
                next_calendar_month = 1
            else:
                EndYear = Year
                next_calendar_month = int(nextmonthInt) + 1

            for weeks in calendar.monthcalendar(int(EndYear), int(next_calendar_month)):
                if i == 1:
                    tempDayValue = weeks[dayOnNumber[day]]
                    if int(week) > 1 and tempDayValue == 0:
                        week = int(week) + 1
                if int(week) == i:
                    endDay = weeks[dayOnNumber[day]]
                if endDay == 0:
                    endDay = weeks[dayOnNumber[day]]
                i = i+1
            if int(nextmonthInt) == 12:
                endMonth = 1
            else:
                endMonth = int(nextmonthInt) + 1

            patchEndDate_str = str(endDay) + "-" +  str(endMonth) + "-" + str(EndYear)
            patchEndDate = datetime.datetime.strptime(patchEndDate_str, '%d-%m-%Y')
            #patchEndDate = patchEndDate + datetime.timedelta(days=int(daysToAdd))
            print("Monthly Patch End Date : ",patchEndDate)
        
        # Finding Start and End date for Quarterly Patching    
        if patchOrderInfo[patchingOccurrence] == "QUARTERLY":
            patchStartDate = None
            quaterlyPatchingMonths = "quarterlyPatchingMonths_" + osPlatform
            monthToStartQuaterly = patchOrderInfo[quaterlyPatchingMonths]
            quaterlyMonths = monthToStartQuaterly.split(",")
            for Q_months in quaterlyMonths:
                if nextmonthStr in Q_months or nextmonthStr == Q_months:
                    print("PATCH TYPE : QUATERLY")
                    print("$$$$$$$$$$$$$ Q_months : ",Q_months)
                    if "+" in Q_months:
                        months = Q_months.split("+")
                        print("$$$$$$$$$$$$$ months : ",months)
                        i = 1
                        for month in months:
                            monthsList.append(month)
                            if i == 1:
                                nextmonthInt = monthOnNumber[month]
                                patchStartDate_str = str("1") + "-" +  str(nextmonthInt) + "-" + str(Year)
                                patchStartDate = datetime.datetime.strptime(patchStartDate_str, '%d-%m-%Y')
                            endMonth = month
                            i = i + 1
                        print("@@@@@@@@@@ End month of Quaterly : ", endMonth)
                        endmonthInt = monthOnNumber[endMonth]
                        endDay = calendar.monthrange(int(Year), int(endmonthInt))[1]
                        patchEndDate_str = str(endDay) + "-" +  str(endmonthInt) + "-" + str(Year)
                        patchEndDate = datetime.datetime.strptime(patchEndDate_str, '%d-%m-%Y')
                        patchEndDate = patchEndDate + datetime.timedelta(hours=23, minutes=59)                                                    
                    else:
                        monthsList.append(Q_months)
                        nextmonthInt = monthOnNumber[Q_months]
                        patchStartDate_str = str("1") + "-" +  str(nextmonthInt) + "-" + str(Year)
                        patchStartDate = datetime.datetime.strptime(patchStartDate_str, '%d-%m-%Y')
                        
                        endmonthInt = monthOnNumber[Q_months]
                        endDay = calendar.monthrange(int(Year), int(endmonthInt))[1]
                        patchEndDate_str = str(endDay) + "-" +  str(endmonthInt) + "-" + str(Year)
                        patchEndDate = datetime.datetime.strptime(patchEndDate_str, '%d-%m-%Y')
                        patchEndDate = patchEndDate + datetime.timedelta(hours=23, minutes=59)                                                    
        
        if patchStartDate == None:
            print("No month is matched for QUATERLY month")
            S3_directory_name = nextmonthStr + "_" + str(S3_directory_year)
            return S3_directory_name,"None"
        else:
            print("Quaterly Patch Start Date : ", patchStartDate)
            print("Quaterly Patch End Date : ",patchEndDate)
        
        ord_No = 1
        for patchGroup1 in patchOrderInfo['totalPatchGroupInOrder']:
            patchGroups = patchGroup1.split(",")
            for patchGroup in patchGroups:
                print(f"patchGroup : {patchGroup} | osPlatform : {osPlatform}")
                selectDowntimeForPatchGroup = []
                print("Patch Group : ",patchGroup)
                print("Schedule Start Date for Patch Group - ", patchGroup, " is : ", patchStartDate)
                print("Schedule End Date for Patch Group - ", patchGroup, " is   : ", patchEndDate)
                #ec2instance = ec2_resource.Instance(instance)
                patchGroupList = []
                for pg in patchGroup.split(","):
                    patchGroupList.append(pg)
                filters = [ {'Name':"tag:Patch Group", 'Values':patchGroupList}]
                ec2instances = ec2_resource.instances.filter(Filters=filters)

                for ec2instance in ec2instances:
                    start_creating_patch_install_on_tag = False
                    print('type of instance is ',type(ec2instance))
                    # if TagName == 'Downtime Window':
                    for tag in ec2instance.tags:
                        if tag["Key"] == TagName:
                            downtime_window_value = tag["Value"]
                            print(f"downtime_window_value : {downtime_window_value}")
                            downtime_window_value = str(downtime_window_value).strip()
                            if downtime_window_value != '':
                                print("SETTING TRUE")
                                start_creating_patch_install_on_tag = True
                    if start_creating_patch_install_on_tag:
                        downtimeFoundForImmediateNextMonth = False
                        if ec2instance.platform == "windows":
                            osName = "windows"
                        else:
                            osName = "linux"
                        if osPlatform == osName:
                            print("Working for ec2 Instance     :   ",ec2instance.id)
                            patchInstallOnStr = ""
                            downtimeDay = None
                            for tag in ec2instance.tags:
                                if tag["Key"] == TagName: 
                                    downtimeValue = tag["Value"]
                                    downtimeValue = (str(downtimeValue)).strip()
                                    downtime_window_tag_len = len(downtimeValue.split(" "))
                                    if downtime_window_tag_len == 6:
                                        day = downtimeValue.split(" ")[0]
                                        if day != "*":
                                            day = day.upper()
                                        week = downtimeValue.split(" ")[1]
                                        month = downtimeValue.split(" ")[2]
                                        hour = downtimeValue.split(" ")[3]
                                        minute = downtimeValue.split(" ")[4]
                                        duration = downtimeValue.split(" ")[5]
                                        print("===== >>> ", day, "-", week, "-", month, "-", hour, "-", minute, "-", duration)
                                        
                                        if patchOrderInfo[patchingOccurrence] == "MONTHLY":
                                            if month == "*" or month == nextmonthStr or month == nextToNextMonthStr or nextmonthStr in month or nextToNextMonthStr in month:
                                                nextPatchGroupStartDate,downtimeFoundForImmediateNextMonth = find_patchWindow_for_Server(ec2instance,ec2instance.id,day,week,month,hour,Year,minute,duration,nextmonthInt,nextmonthStr,ord_No,patchStartDate,patchEndDate,selectDowntimeForPatchGroup,nextPatchGroupStartDate,downtimeFoundForImmediateNextMonth,patchGroup)
                                                #print(" nextPatchGroupStartDate ********************** >>>>>>>> ",nextPatchGroupStartDate)
                                                #print(" downtimeFoundForImmediateNextMonth ********************** >>>>>>>> ",downtimeFoundForImmediateNextMonth)
                                                # If downtime is not found for immediate next month, then checking on next to next month as End date of Patch lying on next to next month 
                                                if downtimeFoundForImmediateNextMonth == False:
                                                    print("Downtime cannot make it for ", nextmonthStr, ". Hence, checking on ",nextToNextMonthStr ," month")
                                                    nextPatchGroupStartDate,downtimeFoundForImmediateNextMonth = find_patchWindow_for_Server(ec2instance,ec2instance.id,day,week,month,hour,nextToNextMonth_Year,minute,duration,nextToNextMonthInt,nextToNextMonthStr,ord_No,patchStartDate,patchEndDate,selectDowntimeForPatchGroup,nextPatchGroupStartDate,downtimeFoundForImmediateNextMonth,patchGroup)
                                        
                                        if patchOrderInfo[patchingOccurrence] == "QUARTERLY":
                                            print("Month List : ",monthsList)
                                            checkEC2Month = []
                                            if "," in month:
                                                checkEC2Month = month.split(",")
                                            else:
                                                checkEC2Month.append(month)
                                            print("checkEC2Month : " ,checkEC2Month) #- ['JAN', 'APR', 'JUL']
                                            print("month : ",month) #- JAN,APR,JUL
                                            print("monthsList : ",monthsList) #- ['JUL']
                                            if month == "*" or any(item in monthsList for item in checkEC2Month):
                                                #print("######################### CONDITION IS TRUE ###################### ")
                                                for monthStr in monthsList:
                                                    nextmonthInt = monthOnNumber[monthStr]
                                                    #print("######################### CONDITION IS TRUE ######################   nextmonthInt   " ,nextmonthInt)
                                                    nextPatchGroupStartDate,downtimeFoundForImmediateNextMonth = find_patchWindow_for_Server(ec2instance,ec2instance.id,day,week,month,hour,Year,minute,duration,nextmonthInt,monthStr,ord_No,patchStartDate,patchEndDate,selectDowntimeForPatchGroup,nextPatchGroupStartDate,downtimeFoundForImmediateNextMonth,patchGroup)
                                                    if downtimeFoundForImmediateNextMonth == True:
                                                        break
                print("nextPatchGroupStartDate ======== >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> : ",nextPatchGroupStartDate, "\n")    
                if nextPatchGroupStartDate != None:
                    patchStartDate = nextPatchGroupStartDate + datetime.timedelta(days=int(patchOrderInfo['waitDaysBetweenGroups']))                    
            ord_No = ord_No + 1                

        S3_directory_name = nextmonthStr + "_" + str(S3_directory_year)
        return S3_directory_name,patchInstallOnValue
    except:
        print(PrintException())
    
def lambda_handler(event, context):
    global patchOrderInfo,S3_Folder_Name
    global patchInstallOnValue,region
    global patchinstalltag
    global temppatchinstalltag
    patchInstallOnValue = []
    Tagname = event['TagName']
    region = event['region']
    S3_Folder_Name = event['S3_Folder_Name']
    ssm = boto3.client("ssm",config=config)
    if Tagname == 'Downtime Window':
        patchinstalltag = "PatchInstallOn"
        temppatchinstalltag = "PatchInstallTemp"
        PatchGroupOrder = os.environ['PatchGroupOrder']
        ssmParameter = ssm.get_parameter(Name=PatchGroupOrder) #"/DXC/PatchingAutomation/Patch_Group_Order"
    else:
        patchinstalltag = "AdhocPatchInstallOn"
        temppatchinstalltag = "AdhocPatchInstallTemp"
        AdhocPatchGroupOrder = os.environ['AdhocPatchGroupOrder']
        ssmParameter = ssm.get_parameter(Name=AdhocPatchGroupOrder) #"/DXC/AdhocPatchingAutomation/Patch_Group_Order"
    patchOrderInfo = json.loads(ssmParameter['Parameter']['Value'])
    print("\n\nWorking on WINDOWS..........")
    S3_directory_name,tagValuesWindows = generate_patchTags(Tagname,event['S3_Bucket'],"windows")
    print("\n\nWorking on LINUX..........")
    S3_directory_name,tagValuesLinux = generate_patchTags(Tagname,event['S3_Bucket'],"linux")
    S3_directory_name = S3_directory_name + "/" + region
    #print("WINDOWS : ",tagValuesWindows)
    #print("LINUX : ",tagValuesLinux)
    #patchInstallOnValue = tagValuesWindows + tagValuesLinux
    patchJobId = generate_uniqueId()
    jsonTagValues = {}
    jsonTagValues['TagName'] = Tagname
    jsonTagValues['TagValues'] = patchInstallOnValue
    jsonTagValues['S3_Bucket'] = event['S3_Bucket']
    jsonTagValues['S3_directory_name'] = S3_directory_name
    jsonTagValues['S3_Folder_Name'] = S3_Folder_Name
    jsonTagValues['region'] = region
    print(jsonTagValues)
    return jsonTagValues

# simple test cases
if __name__ == "__main__":
    event1 = {"TagName": "Downtime Window","S3_Bucket": "dxc","region":"ap-south-1"}
    
    lambda_handler(event1, "")
