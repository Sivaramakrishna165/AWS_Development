var async = require('async');
var AWS = require('aws-sdk');

//AWSPE-6006: Update the AWS api object to perform Exponential Backoff
AWS.config.update({retryDelayOptions: {base: 500}});
var max_retry = 10

var backuputil = require('backuputil');
    exports.handler = (event, context, callback) => {
        //console.log("Event:",event);
        console.log('Event:', JSON.stringify(event, null, 2));
        var instance = event.instances;
    makeSnapshot(instance).then((result) => {
      deleteMessage(event.handle);
      backuputil.deletetagInstanceAsAttempted(instance.InstanceId);
    }).catch((error) => console.log(error));
  }

  function makeSnapshot(instance) {
    let instanceID = instance.InstanceId;
    var OSName = backuputil.getOSName(instance)
    let ErrorMessage = 'Error';
    let BackupSNSTopic = process.env.BackupSNSTopic;
    var snapShotTags = backuputil.getSnapShotTagsLinuxString(instance);
    var serviceRoleArn = process.env.LambdaRoleBackupHandlerArn;
    var docName = process.env.LinuxLevel2BackupDoc;
    var ssm = new AWS.SSM({maxRetries: max_retry});
    var params = {
      DocumentName: docName,
      InstanceIds: [instanceID],
      ServiceRoleArn: serviceRoleArn,
      NotificationConfig: {
        NotificationArn: BackupSNSTopic,
        NotificationEvents: ['Failed','TimedOut'],
        NotificationType: 'Command'
      },
      Parameters: {
        'instanceTags' : [snapShotTags],
        'osName':[OSName]
      }
    }
    return new Promise((resolve,reject) => {
      async.retry({
        times: 8,
        interval: function (retryCount) {
            // Backoff interval between retries, 2 secs, 4 secs, 8 secs, 16 secs.
            let waitTime = 1000 * Math.pow(2, retryCount);
            console.log('SSM Send Command: Exponential Backoff count:'+retryCount+ ', waitTime millisec:'+waitTime);
            
            return waitTime
        }
      },
      function (sccb) {
          ssm.sendCommand(params, function(err, data) {
            if (err) {
              console.log("Error",err);
              console.log("SnapShot Creation for " + instanceID + " failed.");
              sccb(err);
            } else {
              sccb(null, data);
            } 
          });
        },
        function (err, result) {
            if (err) {
              console.log(err)
              let message = 'Error creating snapshot for ' + instanceID;
              let msgData = {};
              msgData.requestParameters = params;
              msgData.request = 'levelTwoLinuxBackup';
              backuputil.pushMessage(ErrorMessage, message, msgData, err);
              reject(err);
            } else {
              resolve(result);
            }
        });
    });
   
  }
  function deleteMessage(handle) {
   let ErrorMessage = 'Error';
    console.log("queueURL:",process.env.QueueUrl);
var sendMsgParams = {
    ReceiptHandle: handle,
    QueueUrl: process.env.QueueUrl,
};
console.log("sendMsgParams:",sendMsgParams);
let sqsClient = new AWS.SQS({region: process.env.AWS_REGION, maxRetries: max_retry});
async.retry({
  times: 8,
  interval: function (retryCount) {
      // Backoff interval between retries, 2 secs, 4 secs, 8 secs, 16 secs.
      let waitTime = 500 * Math.pow(2, retryCount);
      console.log('Sqs delete message: Exponential Backoff count:'+retryCount+ ', waitTime millisec:'+waitTime);
      
      return waitTime
  }
},
    function (delm) {
        sqsClient.deleteMessage(sendMsgParams, function(err, data) {
            if (err){
                console.log(err, err.stack); // an error occurred
            }
            else{
                console.log('Delete Message Success data:',data);           // successful response
            }
        });
    },

    function (err, result) { 
        if (err) {
            console.log('Error during Delete Message: ', err.message);
            let message = 'An error occurred deleting message from queue.';
            let msgData = {};
            msgData.operation = 'deleteMessage';
            msgData.requestParameters = sendMsgParams;
            backuputil.pushMessage(ErrorMessage, message, msgData, err);
        }
        
    });

}

