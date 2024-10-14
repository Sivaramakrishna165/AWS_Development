var async = require('async');
var AWS = require('aws-sdk');
var backuputil = require('backuputil');

//AWSPE-6006: Update the AWS api object to perform Exponential Backoff
AWS.config.update({retryDelayOptions: {base: 500}});
var max_retry = 10

//function levelOneBackup(instance){
    exports.handler = (event, context, callback) => {
    //console.log("Event:",event);
    console.log('Event:', JSON.stringify(event, null, 2));
    let snapshot = [];
    var instance = event.instances;
    var OSName = backuputil.getOSName(instance);
    var blkDeviceMappings = instance.BlockDeviceMappings;
    var outpostArn = null;
    if(instance.hasOwnProperty('OutpostArn'))
    {
        outpostArn = instance.OutpostArn;
        //console.log('outpostArn - ',outpostArn);
        let outpostArn_value = sanitizeConsoleLogs(outpostArn)
        console.log('outpostArn - ', outpostArn_value);
    }
    var deleteOnDate = backuputil.getDeleteOnDate(instance);
    // console.log('deleteOnDate - '+deleteOnDate);
    for (var k = 0; k < blkDeviceMappings.length; k++) {
        var dev = blkDeviceMappings[k];
        var ebs = dev.Ebs;
        if (ebs != null) {
            //console.log('Volume ID - '+ ebs.VolumeId+ ' instance '+ instance+ ' deleteOnDate '+ deleteOnDate);
            let other_logs = sanitizeConsoleLogs(ebs.VolumeId, instance, deleteOnDate)
            console.log('other Logs - ', other_logs);            
             snapshot.push( makeSnapshot(ebs.VolumeId, instance, deleteOnDate, OSName, outpostArn));
        }
    }
         
         Promise.allSettled(snapshot).then((result)=> {
             console.log("Result of all volume is ", result)
             deleteMessage(event.handle);
             backuputil.deletetagInstanceAsAttempted(instance.InstanceId);
         }).catch((error) => console.log(error));
    
   }

  function sanitizeConsoleLogs(...values) {
        return values.map(value => {
            return String(value);
        }).join(' ');
  }    
  
  function makeSnapshot(volumeId, instance, delete_on_date, OSName, outpostArn) {
    //console.log(volume);
    console.log("Start Create Snapshot for Instance:"+instance.InstanceId+" for volume with Id:"+volumeId.toString());
    var snapShotTags = backuputil.getSnapshotTags(instance, delete_on_date);
    let ErrorMessage = "Error";
    var descString = 'Basic EBS snapshot of ' + OSName + ' Volume';
    var ec2 = new AWS.EC2({maxRetries: max_retry});
    // console.log(snapShotTags);
    // console.log(delete_on_date);
    if(outpostArn == null)
    {
        var snapshot_params = {
            Description: descString, 
            VolumeId: volumeId.toString(),
            TagSpecifications: [
              {
                ResourceType: 'snapshot',
                "Tags": snapShotTags
              },
            ],
            DryRun: false
        };
    }
    else{
        var snapshot_params = {
            Description: descString, 
            VolumeId: volumeId.toString(),
            OutpostArn: outpostArn,
            TagSpecifications: [
              {
                ResourceType: 'snapshot',
                "Tags": snapShotTags
              },
            ],
            DryRun: false
        };
    }

    async.retry({
        times: 8,
        interval: function (retryCount) {
            // Backoff interval between retries, 2 secs, 4 secs, 8 secs, 16 secs.
            let waitTime = 500 * Math.pow(2, retryCount);
            console.log('EC2 Create Snapshot: Exponential Backoff count:'+retryCount+ ', waitTime millisec:'+waitTime);
            
            return waitTime
        }
      },
        function (cscb) {
            ec2.createSnapshot(snapshot_params, function (err, data) {
                if (err) {
                    console.log("Error during creation of snapshot:",err);
                    cscb(err);
                } else {
                    if(outpostArn == null){
                        console.log("Snapshot Created in region: ",data.SnapshotId);
                     }
                     else{
                         console.log("Snapshot Created in OutPost: ",data.SnapshotId);
                     }
                    var snapshotId = data.SnapshotId;
                    cscb(null, data);
                }
            });
        },
        function (err, result) {
            if (err) {
                console.log('Error during createSnapshot: ', err.message);
                let message = 'An error occurred during the create snapshot process.';
                let msgData = {};
                msgData.operation = 'createSnapshot';
                msgData.requestParameters = snapshot_params;
                backuputil.pushMessage(ErrorMessage, message, msgData, err);
            }
        });
}

function deleteMessage(handle) {
   
            console.log("queueURL:",process.env.QueueUrl);
            let ErrorMessage = "Error";
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