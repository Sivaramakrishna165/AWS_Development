/**
 *              Copyright (c) 2017 DXC Technologies
 */

/**
  This lambda is responsible for creating snapshots of Instance volumes.  Several setup steps
  are required:

  - The Instances to be processed are tagged with Backup=true (case-insensitive)
  - An optional tag is used to determine the backup schedule to use: BackupSchedule=<Schedule>

  The event that is passed to this lambda typically looks like this:

  { resources: [Create], BackupSchedule: schedule }

  If the BackupSchedule is null, blank, or equal to 'Default' then the standard backup schedule applies.
  Any other value is defined to be a custom backup schedule.  Instances with the tag BackupSchedule
  set to this value will be backed up.

  This lambda also processes deletion of snapshot that have exceeded their expiration date.  The
  event passed to trigger that processing is:

  { resources: [Delete] }

  The backups are triggered by CloudWatch events that are scheduled bases on a Cron expression.
  There is one default backup job that does snapshots for all Instances that are not on a
  custom schedule.  These instances have a blank BackupSchedule tag.

  Custom schedules can also be added to the system to perform snapshots at different intervals,
  such as twice daily.  These scheduled backups are associated with a BackupSchedule.  When this lambda
  runs with a custom BackupSchedule, all Instances that have Backup=true (case-insensitive) and have 
  the BackupSchedule equal to the custom tag will be snapshot'ed.

  EC2 calls to test for error messages:
  - describeLogStreams
  - describeInstances
  - describeVolumes
  - createSnapshot
  - createTags
  - describeSnapshots
  - deleteSnapshot

*/

'use strict';
var AWS = require('aws-sdk');
var moment = require('moment');
var async = require('async');
var sleep = require('system-sleep');
var backuputil = require('backuputil');

//AWSPE-6006: Update the AWS api object to perform Exponential Backoff
AWS.config.update({retryDelayOptions: {base: 500}});
var max_retry = 10

var ec2 = new AWS.EC2({maxRetries: max_retry});
var cwe = new AWS.CloudWatchEvents({maxRetries: max_retry});
var lam = new AWS.Lambda({maxRetries: max_retry});

//  CloudWatch and SNS definitions:
var BackupSNSTopic = 'BackupMessageTopic';

//  Message Types:
var InformationMessage = 'Information';

var ErrorMessage = 'Error';

var optionalTag = null;
var accountId = '123456789';

var prefix = 'Snapshot-Schedule-';

var lambdaWaitTime = null;
var selfName = null;

var queuePresent = 'No';
var queuename = '';
var queueurl = '';
var instances_tobe_backed_list = [];
var maxNumberOfInstances = 0;


exports.handler = (event, context, callback) => {
  console.log('Received event:', JSON.stringify(event, null, 2));
  console.log('Received context:', JSON.stringify(context, null, 2));
  BackupSNSTopic = process.env.BackupSNSTopic;
  queuename = process.env.BackupSQSQueue;
  selfName = context.functionName;
  lambdaWaitTime = parseInt(process.env.LambdaWaitTime) * 1000;
  
  try{
    console.log('Parameter MaxNumberOfInstances = ' + process.env.MaxNumberOfInstances );
    console.log('Parameter LambdaWaitTime = ' + process.env.LambdaWaitTime);
    console.log('Received event :', JSON.stringify(event, null, 2));

    var event_name = JSON.stringify(event.resources);
    optionalTag = event.BackupSchedule; //  Tells which Instances to backup, if specified.
    // If this is a self invocation i.e. continueLambda()
    if (backuputil.isBlank(optionalTag)) {
        optionalTag = 'Default';
    }
    // console.log('Running backup schedule: ', optionalTag);

    accountId = context.invokedFunctionArn.match(/\d{3,}/)[0];
    var continueValue = event.continue;
    if (event_name.indexOf('Create') > -1) {
        console.log('Snapshot Create Event Fired');
        startBackups(event);
        callback(null, 'SNAPSHOT CREATION INITIATED');
    } else if (event_name.indexOf('Delete') > -1) {
        console.log('Snapshot Delete Event Fired');
        removeTagsFromProcessedInstances();
        deleteBackups();
       callback(null, 'SNAPSHOT DELETION INITIATED');
    }
  } catch (err) {
    // No retries on error
    console.log(err);
    return callback(null);
  }
  return callback(null);
};

function startBackups(event) {
    			
        console.log('populate the messages to queue. call populateMessagesToSQS.its a NOT self invocation');
        populateMessagesToSQS();
        console.log('populateMessagesToSQS is completed');
  
}
function populateMessagesToSQS() {
    console.log('Retrieving all the instances. inside populateMessagesToSQS');

    var instParams = {
        Filters: [
            {
                Name: 'tag-key',
                Values: ['EbsVolumeBackupLevel']
            }
        ]
    };
    if(optionalTag !== 'Default') {
        instParams.Filters.push({Name: 'tag:BackupSchedule', Values:[optionalTag]});
    }
    var getQueueparams = {
        QueueName: queuename
    };

	async.retry({
        times: 8,
        interval: function (retryCount) {
            // Backoff interval between retries, 2 secs, 4 secs, 8 secs, 16 secs.
            let waitTime = 500 * Math.pow(2, retryCount);
            console.log('EC2 Describe Instances: Exponential Backoff count:'+retryCount+ ', waitTime millisec:'+waitTime);
            
            return waitTime
        }
      },
        //add describe instances code here
        function (desi) {
            getSchedules().then((result) => {
            console.log("Schedule map result:",result);
            ec2.describeInstances(instParams, function (err, data) {
                if (err) {
                    desi(err);
                } else {
                    console.log('In describeInstances func:',data.Reservations.length);
                    console.log("Reservations:", data.Reservations);
                    var instances = data.Reservations.map((elem) => elem.Instances).flat();
                    console.log("Flatten:", instances);
                     
                        for(var j = 0; j< instances.length; j++){
                           sendMessage(instances[j],result,optionalTag);
                           
                        }
                        
                    console.log('sendMessage|populateMessagesToSQS completed');
                }
            })}) .catch((error)=> console.log(error));
            
        },

        function (err, result) { //  Error on describeInstances:
            if (err) {
                console.log('Error during describeInstances: ', err.message);
                let message = 'An error occurred retrieving Instances for snapshots.';
                let msgData = {};
                msgData.operation = 'describeInstances';
                msgData.requestParameters = getQueueparams;
                //pushMessage(ErrorMessage, message, msgData, err);
            }
        });


}


function sendMessage(instanceItems,schedule, backupSchedule) {
    
    console.log('send the instances to queue: inside sendMessage');
    console.log('instanceID:',instanceItems);

 
            console.log("queueURL:",process.env.QueueUrl);
        var sendMsgParams = {
            MessageBody: JSON.stringify({"instances":instanceItems, "schedule":schedule, "backupSchedule":backupSchedule}),/* required */
            QueueUrl: process.env.QueueUrl,
        };
        console.log("sendMsgParams:",sendMsgParams);
        let sqsClient = new AWS.SQS({region: process.env.AWS_REGION, maxRetries: max_retry});
        async.retry({
            errorFilter: function (err) {
                var retryable = err.retryable;
                return (retryable && retryable == true);
            },
            times: 8,
            interval: function (retryCount) {
                return 10000 * retryCount; //  10 seconds, 20 seconds, 30 seconds, etc.
            }
        },
            function (senm) {
                sqsClient.sendMessage(sendMsgParams, function(err, data) {
                    if (err){
                        console.log(err, err.stack); // an error occurred
                    }
                    else{
                        console.log('sendMessage Success data:',data);           // successful response
                    }
                });
            },
    
            function (err, result) { 
                if (err) {
                    console.log('Error during sendMessage: ', err.message);
                    let message = 'An error occurred sending message to queue.';
                    let msgData = {};
                    msgData.operation = 'sendMessage';
                    msgData.requestParameters = sendMsgParams;
                    backuputil.pushMessage(ErrorMessage, message, msgData, err);
                }
                
            });

}

function getSchedules() {
    let scheduleMap = {};
    //  Eventually, this will retrieve all the backup schedules and determine when there
    //  'should' be a backup for a volume.
    console.log('Retrieving backup schedules...');
    scheduleMap['Default'] = 24; //  Default schedule is for backups every 24 hours.

    //var hourUTC = moment().utc().hour();
    //console.log('Current UTC hour is: ', hourUTC);
    //  Get the custom schedules.  The only thing we know is that the schedule name start with 'Snapshot-Schedule-'
    return new Promise((resolve, reject) => {var params = {
        NamePrefix: prefix
    };
    cwe.listRules(params, function (err, data) {
        if (err) {
            reject(err);
        } else {
            var schedules = data.Rules;
            for (var s = 0; s < schedules.length; s++) {
                var schedule = schedules[s];
                var scheduleName = schedule.Name;
                var scheduleExpression = schedule.ScheduleExpression;
                console.log('Found custom schedule: ', scheduleName, ' at times: ', scheduleExpression);
                if (scheduleName && scheduleExpression) {
                    //  Strip off Backup-Schedule- from the name:
                    var name = scheduleName.replace(prefix, '');
                    if (name == 'Default') {
                        //  Someone added a custom schedule with a tag of Default - ignore this:
                        console.log('Ignoring custom schedule with tag: Default.  Please delete this schedule');
                        let message = 'Ignoring custom schedule with tag: Default.  Please delete this schedule';
                        let msgData = {};
                        backuputil.pushMessage(InformationMessage, message, msgData, null);
                        break;
                    }
                    scheduleMap[name] = 24; //  Doesn't matter what hour we use here - just save the schedule name.
                }
            }
            resolve(scheduleMap);
        }
    });
});
}

function removeTagsFromProcessedInstances(){

  //  Query for all Instances that have a Backup tag:
  var params = {
      Filters: [
          {
              Name: 'tag-key',
              Values: ['BackupAttempted']
          }
      ]
  };
  console.log('Removing BackupAttempted tags');
  async.retry({
      errorFilter: function (err) {
          var retryable = err.retryable;
          return (retryable && retryable == true);
      },
      times: 8,
      interval: function (retryCount) {
          return 10000 * retryCount; //  10 seconds, 20 seconds, 30 seconds, etc.
      }
  },
      function (rts) {
        ec2.describeInstances(params, function (err, data) {
            if (err) {
              rts(err);
            } else {
              for (var res = 0; res < data.Reservations.length; res++) {
                var instances = data.Reservations[res].Instances;
                for (var j = 0; j < instances.length; j++){
                  var instanceID = instances[j].InstanceId;
                  sleep(1000);
                  deletetagInstanceAsAttempted(instanceID)
                }
              }
            }
          rts(null)
        });    
      },
      function (err, result) { //  Error on describeInstances:
          if (err) {
              console.log('Error during describeInstances: ', err.message);
              let message = 'An error occurred retrieving Instances for snapshots.';
              let msgData = {};
              msgData.operation = 'describeInstances';
              msgData.requestParameters = params;
              backuputil.pushMessage(ErrorMessage, message, msgData, err);
          }
      });
}

function deletetagInstanceAsAttempted(instanceID){
  //Remove BackupAttemptedtag instance after backups completed.
  var params = {
   Resources: [instanceID], 
   Tags: [{
     Key: "BackupAttempted", 
     Value: "true"
    }
  ]};
  async.retry({
      errorFilter: function (err) {
          var retryable = err.retryable;
          return (retryable && retryable == true);
      },
      times: 8,
      interval: function (retryCount) {
          return 10000 * retryCount; //  10 seconds, 20 seconds, 30 seconds, etc.
      }
  },
    function (rts) {
      ec2.deleteTags(params, function(err, data) {
        if (err) {
          console.log(err, err.stack);
          rts(err,data)
        }  else {
          console.log("BackupAttempted tag removed from " + instanceID);
          rts(null);
        }
      });
    },
  function (err, result) { //  Error on describeInstances:
      if (err) {
          console.log('Error during describeInstances: ', err.message);
          let message = 'An error occurred retrieving Instances for snapshots.';
          let msgData = {};
          msgData.operation = 'describeInstances';
          msgData.requestParameters = params;
          backuputil.pushMessage(ErrorMessage, message, msgData, err);
      }
  });
}

function continueLambda(optionalTag){
  
  var payload = {
    "BackupSchedule" : optionalTag,
    "resources": ["Create"],
	"SelfInvocation": ["True"]
  }
  var payloadString = JSON.stringify(payload)
  var params = { 
    FunctionName: selfName,
    InvocationType: "Event", 
    Payload: payloadString, 
  }

  lam.invoke(params, function(err, data) {
    if (err) console.log(err, err.stack);
    else     console.log('Lambda backupHandler Invoked');
  });
}


function getDeleteOnDate(instance) {
    var instanceTags = instance.Tags;

    //  Default to 30 days just in case:
    var today = moment();
    var deleteDate = moment(today).add('30', 'day');
    var deleteOnDate = moment(deleteDate).utc().format('YYYY-MM-DD');

    for (var k = 0; k < instanceTags.length; k++) {
        var instanceKeyTag = instanceTags[k].Key;
        //console.log('INSTANCE TAG KEY : ' + instanceKeyTag);
        var instanceValueTag = instanceTags[k].Value;
        //console.log('INSTANCE TAG VALUE : ' + instanceValueTag);

        if (instanceKeyTag == 'RetentionPeriod') {
            var retentionDate = instanceValueTag;
            deleteDate = moment(today).add(retentionDate, 'day');
            deleteOnDate = moment(deleteDate).utc().format('YYYY-MM-DD');
        }
    }
    return deleteOnDate;
}



function getSnapshotTags(instance) {
    //  This tag determines when to delete the snapshot:
    var delete_on_date = getDeleteOnDate(instance)
    var deleteOnTag = {
        Key: 'DeleteOn',
         Value: delete_on_date.toString()
    };
    
    //console.log('Adding tags to snapshot: ', snapshot_id);
    var snapShotTags = instance.Tags;
    
    // These are the instance tags we want to apply to the snapshots
    var keepTags = ['Application','Compliance','Environment','InstanceName','Project','Owner'];
    // Iterate through snapShotTags tags
    for (var i = 0; i < snapShotTags.length; i++) {
        var keep = false;
        var key = snapShotTags[i].Key;

        //Check for tags to keep 
        for (var j = 0; j < keepTags.length; j++){
           var tag = keepTags[j];
           if (key.startsWith(tag)){
                keep = true;
           }  
        } 
        //remove tags not in SnapshotTags
        if ( keep != true){
            snapShotTags.splice(i,1);
            i--;
        }
    }

    //  Propagate the Instance ID:
    var name = 'InstanceId: ' + instance.InstanceId;
    var nameTag = {
        Key: 'Name',
        Value: name
    };

    snapShotTags.push(deleteOnTag);
    snapShotTags.push(nameTag);
    
    return snapShotTags;
}


function deleteBackups() {

    var params = {
        OwnerIds: ['self']
    };

    async.retry({
        errorFilter: function (err) {
            var retryable = err.retryable;
            return (retryable && retryable == true);
        },
        times: 8,
        interval: function (retryCount) {
            return 10000 * retryCount; //  10 seconds, 20 seconds, 30 seconds, etc.
        }
    },
        function (dscb) {
            ec2.describeSnapshots(params, function (err, data) {
                if (err) {
                    dscb(err);
                } else {
                    var snapshots = data.Snapshots;

                    var now = moment();
                    console.log('Deleting snapshots older than: ', now);

                    for (var i = 0; i < snapshots.length; i++) {
                        var tags = snapshots[i].Tags;
                        for (var j = 0; j < tags.length; j++) {
                            var nameOfTag = tags[j].Key;
                            if (nameOfTag == 'DeleteOn') {
                                var valueOfTag = tags[j].Value;
                                var deleteOnDate = moment(valueOfTag);
                                //console.log('Delete date is: ', deleteOnDate);
                                if (deleteOnDate < now) {
                                    var snapshotId = snapshots[i].SnapshotId;
                                    //deleteSnapshots(snapshotId);
                                    if(snapshots[i].Description.includes('Created by CreateImage')){
                                        console.log('Created by CreateImage: Dont delete:',snapshotId);
                                    }else{
                                        console.log('Created by backup: delete:',snapshotId);
                                        deleteSnapshots(snapshotId);
                                    }
                                }
                            }
                        }
                    }
                    dscb(null, data);
                }
            });
        },
        function (err, result) {
            if (err) {
                console.log('Error during describeSnapshots: ', err.message);
                let message = 'An error occurred describing snapshots.';
                let msgData = {};
                msgData.operation = 'describeSnapshots';
                msgData.requestParameters = {};
                backuputil.pushMessage(ErrorMessage, message, msgData, err);
            } 
        });
}

function deleteSnapshots(snapId) {
    console.log('Deleting snapshot: ', snapId);

    var snapshot_params = {
        SnapshotId: snapId
    };

    async.retry({
        times: 8,
        interval: function (retryCount) {
            return 10000 * retryCount; //  10 seconds, 20 seconds, 30 seconds, etc.
        }
    },
        function (dscb) {
            ec2.deleteSnapshot(snapshot_params, function (err, data) {
                if (err) {
                    dscb(err);
                } else {
                    dscb(null, data);
                }
            });
        },
        function (err, result) {
            if (err) {
                console.log('Error during deleteSnapshot: ', err.message);
                let message = 'An error occurred deleting a snapshot.';
                let msgData = {};
                msgData.operation = 'deleteSnapshot';
                msgData.requestParameters = snapshot_params;
                backuputil.pushMessage(ErrorMessage, message, msgData, err);
            }
        });
}
