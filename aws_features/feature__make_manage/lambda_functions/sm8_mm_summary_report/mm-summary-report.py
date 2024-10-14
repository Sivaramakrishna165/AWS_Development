import boto3, json
from create_summary_report import generate_mm_summary_report
sg_client = boto3.client('stepfunctions')

# Send task success to step function
def send_task_success(taskToken, payload_json):
    try:
        response = sg_client.send_task_success(
            taskToken=taskToken,
            output = json.dumps(payload_json)
        )
        print('Task SUCCESS token sent - ',response)

    except Exception as e:
        print('Error send_task_success()-',e)

# Send task failure to step function
def send_task_failure(taskToken, error, cause):
    try:
        response = sg_client.send_task_failure(
            taskToken=taskToken,
            error = error,
            cause = cause
        )
        print('Task FAILURE token sent - ',response)

    except Exception as e:
        print('Error send_task_success()-',e)

def lambda_handler(event, context):
    
    try:
        print('Event - ', event)
        print('Context - ', context)
        status = "SUCCESS"
        error_message = ''
        if('Error' in event):
            try:
                error_json = json.loads(event['Error'])
            except Exception as e:
                print('Not Valid Json Format', str(e))
                error_json = event['Error']
            instanceId = error_json['InstanceId']
            error_message = "For " +  instanceId + " : STEP : " + error_json['Error']  + ' Cause : ' + event['Cause']
            status = "FAIL"
        if('TaskToken' in event):
            taskToken = event['TaskToken']
            instanceId = event['InstanceId']
    
        error = {}
        error['InstanceId'] = instanceId

        region = context.invoked_function_arn.split(':')[3]
        create_report_object = generate_mm_summary_report(region)
        create_report_object.updateMMTag(instanceId, 'dxc_make_manage', status)
        create_report_object.update_report_table(instanceId, status)
        latest_report_list = create_report_object.create_latest_report_list(instanceId)
        
        if status == "SUCCESS":
            print("latest_report_list is ", latest_report_list)
            return "Lambda executed successfully"
        else:
            print("SSM Report Generation Failed -", error_message)
            
    except Exception as e:
        print('Lambda exception Occurred', str(e))
        raise
        