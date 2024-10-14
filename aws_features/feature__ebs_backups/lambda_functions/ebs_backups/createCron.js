/**
 *              Copyright (c) 2017 DXC Technologies
 */

/*
*  This Lambda takes a create resource event call from CF and creates a cron
*  expression (string) from the inputs.
* 
*/


exports.handler = function (event, context) {
    console.log('REQUEST RECEIVED:\n', JSON.stringify(event));

    //  The DELETE method will be called when the custom resource is deleted (when the CF Stack is deleted)
    if (event.RequestType == 'Delete' || event.RequestType == 'Update') {
        sendResponse(event, context, 'SUCCESS');
        return;
    }

    //  Currently supports a list of hours.  Maybe support other parameters?  Days of week?  Minute offset?
    var hours = event.ResourceProperties.Hours;

    if (hours == null) {
        hours = [];
    }

    var hoursExpression = '0'; //  Default to backups at 12AM UTC if no hours defined:
    if (hours.length > 0) {
        hoursExpression = '';
        for (var i = 0; i < hours.length; i++) {
            if (i > 0) {
                hoursExpression += ',';
            }
            hoursExpression += hours[i];
        }
    }

    var cron = 'cron(0 ';
    cron += hoursExpression;
    cron += ' * * ? *)';
    //console.log('Generated cron expression: ', cron);
    console.log('Generated cron expression: ', JSON.stringify(cron, null, 2));
    var responseStatus = 'SUCCESS';
    var responseData = {};
    responseData.CronExpression = cron;
    sendResponse(event, context, 'SUCCESS', responseData);
};



// Send response to the pre-signed S3 URL 
function sendResponse(event, context, responseStatus, responseData) {

    var responseBody = JSON.stringify({
        Status: responseStatus,
        Reason: 'See the details in CloudWatch Log Stream: ' + context.logStreamName,
        PhysicalResourceId: context.logStreamName,
        StackId: event.StackId,
        RequestId: event.RequestId,
        LogicalResourceId: event.LogicalResourceId,
        Data: responseData
    });

    console.log('RESPONSE BODY:\n', responseBody);

    var https = require('https');
    var url = require('url');

    var parsedUrl = url.parse(event.ResponseURL);
    var options = {
        hostname: parsedUrl.hostname,
        port: 443,
        path: parsedUrl.path,
        method: 'PUT',
        headers: {
            'content-type': '',
            'content-length': responseBody.length
        }
    };

    console.log('SENDING RESPONSE...\n');

    var request = https.request(options, function (response) {
        console.log('STATUS: ' + response.statusCode);
        console.log('HEADERS: ' + JSON.stringify(response.headers));
        // Tell AWS Lambda that the function execution is done  
        context.done();
    });

    request.on('error', function (error) {
        console.log('sendResponse Error:' + error);
        // Tell AWS Lambda that the function execution is done  
        context.done();
    });

    // write data to request body
    request.write(responseBody);
    request.end();
}
