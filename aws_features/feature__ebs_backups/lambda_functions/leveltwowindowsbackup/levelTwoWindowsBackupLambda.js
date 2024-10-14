var async = require('async');
var AWS = require('aws-sdk');
var backuputil = require('backuputil');

//AWSPE-6006: Update the AWS api object to perform Exponential Backoff
AWS.config.update({retryDelayOptions: {base: 500}});
var max_retry = 10

  exports.handler = (event, context, callback) => {
      //console.log("Event:",event);
      console.log('Event:', JSON.stringify(event, null, 2));
      let instance = event.instances;
      makeSnapshot(instance).then((result) => {
      deleteMessage(event.handle);
      backuputil.deletetagInstanceAsAttempted(instance.InstanceId);
    }).catch((error) => console.log(error));
    
  }

  function makeSnapshot(instance) {
    var OSName = backuputil.getOSName(instance)
    var snapShotTags = backuputil.getSnapshotTagsWindowsString(instance);
    var instanceID = instance.InstanceId;
    var serviceRoleArn = process.env.LambdaRoleBackupHandlerArn;
    let BackupSNSTopic = process.env.BackupSNSTopic;
    console.log("Instance ID" + instanceID);
    var ssm = new AWS.SSM({maxRetries: max_retry})
    var params = {
      DocumentName: 'AWSEC2-CreateVssSnapshot',
      InstanceIds: [instanceID],
      ServiceRoleArn: serviceRoleArn,
      NotificationConfig: {
        NotificationArn: BackupSNSTopic,
        NotificationEvents: ['Failed','TimedOut'],
        NotificationType: 'Command'
      },
      Parameters: {
        'description': ['Filesystem-consistent snapshot of ' + OSName + ' Volume.'],
        'ExcludeBootVolume': ['False'],
        'tags' : [snapShotTags]
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
              console.log("SnapShot Creation for " + instanceID + " failed.");
              console.log("err:",err);
              sccb(err);
            } else sccb(null,data);
          });
        
      },
      function (err, result) {
          if (err) {
            console.log(err)
            let message = 'Error creating snapshot for ' + instanceID;
            let msgData = {};
            let ErrorMessage = "Error";
            msgData.requestParameters = params;
            msgData.request = 'levelTwoWindowsBackup';
            backuputil.pushMessage(ErrorMessage, message, msgData, err);
            reject(err);
          } else {resolve(result);}
      }); 

   });
  }
  function deleteMessage(handle) {
   
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
      console.log('SQS Delete Message: Exponential Backoff count:'+retryCount+ ', waitTime millisec:'+waitTime);
      
      return waitTime
  }
},
    function (delm) {
        sqsClient.deleteMessage(sendMsgParams, function(err, data) {
            if (err){
                console.log(err, err.stack); // an error occurred
                delm(err);
            }
            else{
                console.log('Delete Message Success data:',data);
                delm(null,data);           // successful response
            }
        });
    },

    function (err, result) { 
        if (err) {
            console.log('Error during Delete Message: ', err.message);
            let message = 'An error occurred deleting message from queue.';
            let msgData = {};
            let ErrorMessage = "Error";
            msgData.operation = 'deleteMessage';
            msgData.requestParameters = sendMsgParams;
            backuputil.pushMessage(ErrorMessage, message, msgData, err);
        }
        
    });

}


  
  