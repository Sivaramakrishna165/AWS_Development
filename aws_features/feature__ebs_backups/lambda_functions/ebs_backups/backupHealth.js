/**
 *              Copyright (c) 2017 DXC Technologies
 */

/**
  This lambda is responsible for making sure backups are occurring as scheduled.  The basic test
  is to ensure that a backup for a volume exists that is a day or less old.  When custom schedules
  are implemented, we may need to check to see that a backup exists per the custom schedule.

  - The Instances to be processed are tagged with Backup=true (case-insensitive)

*/

'use strict';
var AWS = require('aws-sdk');
var moment = require('moment');
var async = require('async');
var parser = require('cron-parser');

//AWSPE-6006: Update the AWS api object to perform Exponential Backoff
AWS.config.update({retryDelayOptions: {base: 500}});
var max_retry = 10

var ec2 = new AWS.EC2({maxRetries: max_retry});
var cwl = new AWS.CloudWatchLogs({maxRetries: max_retry});
var sns = new AWS.SNS({maxRetries: max_retry});
var cwe = new AWS.CloudWatchEvents({maxRetries: max_retry});
var ssm = new AWS.SSM({maxRetries: max_retry});

//  CloudWatch and SNS definitions:
var BackupLogGroup = 'BackupLogs';
var BackupMessageStream = 'BackupLogMessages';
var BackupSNSTopic = 'BackupMessageTopic';

//  Message Types:
var InformationMessage = 'Information';
var WarningMessage = 'Warning';
var ErrorMessage = 'Error';

var accountId = '123456789';
var verifyList = [];
var scheduleMap = new Map();

var consolidated = {};
var date_time = new Date();
var incidentPriority = '';

exports.handler = (event, context, callback) => {
    //console.log('Received event:', JSON.stringify(event, null, 2));
    var event_name = JSON.stringify(event.resources);
    BackupLogGroup = process.env.BackupLogGroup;
    BackupMessageStream = process.env.BackupMessageStream;
    BackupSNSTopic = process.env.BackupSNSTopic;
    var IncidentPrioritySSMParam = process.env.IncidentPrioritySSMParam;
    incidentPriority = getParameter(IncidentPrioritySSMParam, callback);
    accountId = context.invokedFunctionArn.match(/\d{3,}/)[0];
    verifyList = []; //  For some reason, global variables are not re-cleared.
    scheduleMap = new Map();
    
    console.log('Backup Health Event Fired');
    async.series([
        function (callback) {
            getSchedules(callback);
        },
        function (callback) {
            getVolumesToVerify(callback);
        },
        function (callback) {
            verifyVolumes(callback);
        },
        function (callback){
            report_backup_fail(callback);
        }
    ],
        function (err, results) {
            if (err) {
                console.log(err.message);
            }
        });

    callback(null, 'Backup Health test initiated');
};

var prefix = 'Snapshot-Schedule-';

function getSchedules(callback) {
    //  Eventually, this will retrieve all the backup schedules and determine when there
    //  'should' be a backup for a volume.
    console.log('Retrieving backup schedules...');
    //scheduleMap.set('Default', 24); //  Default schedule is for backups every 24 hours.
    scheduleMap.set('Default', 1440); //  Default schedule is for backups every 1440 minutes ie 24 hours.
    
    var minUTC = moment().utc().minute();
    var hourUTC = moment().utc().hour();
    var dateUTC = moment().utc().date();
    var monthUTC = moment().utc().month()+1;
    var dowUTC = moment().utc().weekday();

    var timeUTC = moment().utc();
    var dowUTC_name = moment().utc().format('dddd');
    dowUTC_name = dowUTC_name.substr(0,3);

    //  Get the custom schedules.  The only thing we know is that the schedule name start with 'Snapshot-Schedule-'
    var params = {
        NamePrefix: prefix
    };
    cwe.listRules(params, function (err, data) {
        if (err) {
            callback(err);
        } else {
            var schedules = data.Rules;
            for (var s = 0; s < schedules.length; s++) {
                var schedule = schedules[s];
                var scheduleName = schedule.Name;
                var scheduleExpression = schedule.ScheduleExpression;
                console.log('Custom schedule: ', scheduleName, ' at times: ', scheduleExpression);
                if (scheduleName && scheduleExpression) {
                    //  Strip off Backup-Schedule- from the name:
                    var name = scheduleName.replace(prefix, '');
                    if (name == 'Default') {
                        //  Someone added a custom schedule with a tag of Default - ignore this:
                        console.log('Ignoring custom schedule with tag: Default.  Please delete this schedule');
                        var message = 'Ignoring custom schedule with tag: Default.  Please delete this schedule';
                        var msgData = {};
                        pushMessage(InformationMessage, message, msgData, null);
                        break;
                    }
                    //  Strip off 'cron(' and ending ')'
                    var expression = scheduleExpression.replace('cron(', '');
                    expression = expression.replace(')', '');
                    var atoms = expression.split(' '); //  get the fields
					// changes made for ticket AWSPE-4554. HealthCheck should not check for the creation of snapshots everyday
					// instead it should check according to cron 
					// Earlier, only 'hour' field used to be fetched from cron and being used in process.
					// now we need to take all the fields from cron
					// convert everything to minutes, as we go with minutes, it would be easy for calculation
                    if (atoms.length == 6) {
						// multiple values may be present in comma separated format
                        var mins = atoms[0];
                        mins = mins.split(',');
                        var hours = atoms[1];
                        hours = hours.split(',');
                        var days = atoms[2];
                        days = days.split(',');
                        var months = atoms[3];
                        months = months.split(',');
                        var dow = atoms[4];
                        dow = dow.split(',');
                        var year = atoms[5];
                        year = year.split(',');

                        //  Find the last minute,hour,month,dow of the schedule less than the current time:
						
                        var lastScheduledHour = hours[hours.length - 1]; 
						var lastScheduledMin = mins[mins.length - 1];
                        if (days[0] != '*' && days[0] != '?') {
                            var lastScheduledDay = days[days.length - 1];
                        }
                        if (months[0] != '*' && months[0] != '?') {
                            var lastScheduledMonth = months[months.length - 1];
                        }
                        if (dow[0] != '*' && dow[0] != '?') {
                            var lastScheduledDow = dow[dow.length - 1];
                        }

                        for (var m = 0; m < mins.length; m++) {
                            var min = Number(mins[m]);
                            if (min < minUTC) {
                                lastScheduledMin = min;
                            }
                        }

                        for (var h = 0; h < hours.length; h++) {
                            var hour = Number(hours[h]);
                            if (hour < hourUTC) {
                                lastScheduledHour = hour;
                            }
                        }

                        if (days[0] != '*' && days[0] != '?') {
                            for (var d = 0; d < days.length; d++) {
                                var day = Number(days[d]);
                                if (day < dateUTC) {
                                    lastScheduledDay = day;
                                }
                            }
                        }else {
                            day = days[0];
                        }

                        if (dow[0] != '*' && dow[0] != '?') {
                            for (var dw = 0; dw < dow.length; dw++) {
                                var dayofweek = Number(dow[dw]);
                                if (dayofweek < dowUTC) {
                                    lastScheduledDOW = dayofweek;
                                }
                            }
                        }else {
                            dayofweek = dow[0];
                        }

                        if (months[0] != '*' && months[0] != '?') {
                            for (var mo = 0; mo < months.length; mo++) {
                                var month = Number(months[mo]);
                                if (month < monthUTC) {
                                    lastScheduledMonth = month;
                                }
                            }
                        }else {
                            month = months[0];
                        }

                        // From the docs it seems to be 1-7 or SUN-SAT , a bit confusing since in UNIX 0 = SUN.
                        if (dayofweek > 1) {
                            dayofweek -= 1;
                        }

                        var cron = '0'+' '+min+' '+hour+' '+day+' '+month+' '+dayofweek;
                        console.log('cron:',cron);
                        var interval = parser.parseExpression(cron);
						//previous cron execution time 
                        var previousCron_time = interval.prev().toString();

                        console.log('Adding test for schedule: ', name, ' and previousCron_time: ', previousCron_time);
                        //  Calculate the minutes ago the backup should have occurred:
                        var lastBackupAge = timeUTC - moment(previousCron_time);
                        lastBackupAge = Math.round(lastBackupAge / 60000);

                        if (lastBackupAge <= 0) {
                            //  We running before the first backup of the day...
                            lastBackupAge += 1440;
                        }
                        lastBackupAge += 60; // So we can run anytime in 60 minute.
                        console.log('lastBackupAge:',lastBackupAge);
                        scheduleMap.set(name, lastBackupAge);
                    } else {
                        console.log('Backup Health does not recognize this schedule: ', scheduleExpression);
                    }
                }
            }
            callback(null);
        }
    });
}

function report_backup_fail(callback){
    console.log('Retrieving volumes to verify...');
    
    async.retry({
        errorFilter: function (err) {
            var retryable = err.retryable;
            return (retryable && retryable == true);
            },
            times: 8,
            interval: function (retryCount) {
                return 10000 * retryCount; //  10 seconds, 20 seconds, 40 seconds, etc.
            }
            },
        function (chk_inst) {
            // console.log(consolidated);
            for(const [key, val] of Object.entries(consolidated)) {
                if(val['Event'] == 'BackupFailure')
                {
                    console.log('No Backup for instanceID ', key, ' Volumes ', val['VolumeIds']);
                    var message = 'A backup for Instance: ' + key + '  volume/volumes - '+val['VolumeIds'] + ' Failed';
                    pushMessage(ErrorMessage, message, val, null);
                }
                else
                {
                    console.log('Backup EXISTS for instanceID ', key);
                }
            }
            chk_inst(null);
        },
        function (err, result) { 
            if (err) {
                console.log('Error during report_backup_fail: ', err.message);
                callback(err.message);
            } else {
                callback(null);
            }
        });
}

function getVolumesToVerify(callback) {
    console.log('Retrieving volumes to verify...');
    //  Query for all Instances that are tagged for Backup:
    var params = {
        Filters: [
            {
                Name: 'tag-key',
                Values: ['EbsVolumeBackupLevel']
            }
        ]
    };

    async.retry({
        errorFilter: function (err) {
            var retryable = err.retryable;
            return (retryable && retryable == true);
        },
        times: 8,
        interval: function (retryCount) {
            return 10000 * retryCount; //  10 seconds, 20 seconds, 40 seconds, etc.
        }
    },
        function (dicb) {
            ec2.describeInstances(params, function (err, data) {
                if (err) {
                    dicb(err);
                } else {
                    //console.log(data);
                    var volumeList = [];
                    var instanceMap = new Map();
                    for (var i = 0; i < data.Reservations.length; i++) {
                        var instances = data.Reservations[i].Instances;

                        for (var j = 0; j < instances.length; j++) {
                            var instanceID = instances[j].InstanceId;
                            var instance = instances[j];
                            consolidated[instanceID] = {};
                            consolidated[instanceID]['InstanceId'] = instances[j].InstanceId;
                            consolidated[instanceID]['VolumeIds'] = [];
                            consolidated[instanceID]['LatestBackup'] = '';
                            consolidated[instanceID]['EventDate'] = date_time;
                            consolidated[instanceID]['Event'] = '';
                            consolidated[instanceID]['IncidentPriority'] = incidentPriority;
                            var backupTagged = false;
                            //  Must have the tag "Backup=true" (case-insensitive tag value) to check for backups.
                            //  Determine which schedule this Instance uses:
                            var backupSchedule = 'Default';
                            for (var t = 0; t < instance.Tags.length; t++) {
                                if (instance.Tags[t].Key == 'EbsVolumeBackupLevel') {
                                    var backupTag = instance.Tags[t].Value;
                                    if (!isBlank(backupTag) && backupTag > '0') {
                                        backupTagged = true;
                                    }
                                } else if (instance.Tags[t].Key == 'BackupSchedule') {
                                    backupSchedule = instance.Tags[t].Value;
                                    if (isBlank(backupSchedule)) {
                                        backupSchedule = 'Default';
                                    }
                                }
                            }
                            if (!backupTagged) {
                                // No "Backup=true" (case-insensitive) tag found
                                continue;
                            }

                            var mins = scheduleMap.get(backupSchedule);
                            if (mins == null) {
                                //  There's an instance with a backup schedule we don't recognize:
                                console.log('The Instance ', instance.InstanceId, ' has an unrecognized backup schedule: ', backupSchedule);
                                var message = 'The Instance ' + instance.InstanceId + ' has an unrecognized backup schedule: ' + backupSchedule;
                                var msgData = {};
                                msgData.InstanceId = instance.InstanceId;
                                msgData.correlation_id = instance.InstanceId;
                                // pushMessage(WarningMessage, message, msgData, null);
                            //  Perform test anyway - use daily schedule as basis of backups
                            }


                            var blkDeviceMappings = instance.BlockDeviceMappings;
                            for (var k = 0; k < blkDeviceMappings.length; k++) {
                                var dev = blkDeviceMappings[k];
                                var ebs = dev.Ebs;
                                if (ebs != null) {
                                    var volId = ebs.VolumeId;
                                    volumeList.push(volId);
                                    instanceMap.set(volId, instance);
                                    // consolidated[instanceID]['VolumeIds'].push(volId);
                                //console.log('Will test backup: ', volId, ' for: ', instance.InstanceId);
                                }
                            }
                        }
                    }
                    //  Could be no Instances are tagged for this schedule or tagged at all!
                    if (volumeList.length == 0) {
                        console.log('No Instances found for backups.');
                        var message = 'There were no Instances found for this backup schedule.';
                        var msgData = {};
                        msgData.requestParameters = params;
                        pushMessage(InformationMessage, message, msgData, null);
                        dicb(null);
                        return;
                    }

                    //  Describe all volumes from the Instances tagged for backups:
                    var describeVolumes_params = {
                        VolumeIds: volumeList
                    };
                    //console.log(describeVolumes_params);
                    async.retry({
                        errorFilter: function (err) {
                            var retryable = err.retryable;
                            return (retryable && retryable == true);
                        },
                        times: 8,
                        interval: function (retryCount) {
                            return 10000 * retryCount; //  10 seconds, 20 seconds, 40 seconds, etc.
                        }
                    },
                        function (dvcb) {
                            ec2.describeVolumes(describeVolumes_params, function (err, data) {
                                if (err) {
                                    dvcb(err);
                                } else {
                                    //console.log(data);
                                    var volumes = data.Volumes;
                                    for (var v = 0; v < volumes.length; v++) {
                                        var volume = volumes[v];
                                        var volId = volume.VolumeId;
                                        var instance = instanceMap.get(volId);

                                        //  Determine which schedule this Instance uses:
                                        var backupSchedule = 'Default';
                                        for (var i = 0; i < instance.Tags.length; i++) {
                                            if (instance.Tags[i].Key == 'BackupSchedule') {
                                                backupSchedule = instance.Tags[i].Value;
                                                if (isBlank(backupSchedule)) {
                                                    backupSchedule = 'Default';
                                                }
                                            }
                                        }
                                        var mins = scheduleMap.get(backupSchedule);
                                        if (!mins){
                                            mins = 1440;
                                        } //  In case the Instance has a schedule that doesn't exist!
                                        var verifyRequest = {
                                            Instance: instance,
                                            Volume: volume,
                                            LastBackupTime: mins,
                                            ScheduleName: backupSchedule
                                        };
                                        //console.log('Queueing snapshot verify for Volume: ', volId, ' on Instance: ', instance.InstanceId);
                                        verifyList.push(verifyRequest);
                                    }
                                    dvcb(null);
                                }
                            });
                        },
                        function (err, result) {
                            if (err) {
                                console.log('Error during describeVolumes: ', err.message);
                                var message = 'An error occurred retrieving the Volumes for backup.';
                                var msgData = {};
                                msgData.operation = 'describeVolumes';
                                msgData.requestParameters = describeVolumes_params;
                                pushMessage(ErrorMessage, message, msgData, err);
                                dicb(err.message);
                            } else {
                                dicb(null);
                            }
                        });
                }
            });
        },
        function (err, result) { //  Error on describeInstances:
            if (err) {
                console.log('Error during describeInstances: ', err.message);
                var message = 'An error occurred retrieving Instances for snapshots.';
                var msgData = {};
                msgData.operation = 'describeInstances';
                msgData.requestParameters = params;
                pushMessage(ErrorMessage, message, msgData, err);
                callback(err.message);
            } else {
                callback(null);
            }
        });
}


function verifyVolumes(callback) {
    console.log('Verifying snapshots for volumes...');
    //console.log(verifyList);

    async.eachSeries(verifyList, verifySnapshots, function (err) {
        if (err) {
            callback(err);
        } else {
            callback(null);
        }
    });
}

function verifySnapshots(request, callback) {

    console.log('verifySnapshots request:',request);
    var instance = request.Instance;
    var volume = request.Volume;
    var mins = request.LastBackupTime;
    var scheduleName = request.ScheduleName;

    console.log('instance:',instance,'| volume:',volume,' |mins:',mins,' |scheduleName:',scheduleName);

    var backupMinimumDate = moment().subtract(mins, 'minutes');
    var volume_id = volume.VolumeId;
    console.log('Verifying snapshots for: ', instance.InstanceId, '/', volume_id, ' for schedule: ', scheduleName, ' in the last ', mins, ' mins.');

    //  Describe all snapshots for this volume:
    var describeSnapshots_params = {
        Filters: [
            {
                Name: 'volume-id',
                Values: [
                    volume_id
                ]
            }
        ]
    };
    async.retry({
        errorFilter: function (err) {
            var retryable = err.retryable;
            return (retryable && retryable == true);
        },
        times: 8,
        interval: function (retryCount) {
            return 10000 * retryCount; //  10 seconds, 20 seconds, 40 seconds, etc.
        }
    },
        function (dscb) {
            ec2.describeSnapshots(describeSnapshots_params, function (err, data) {
                if (err) {
                    dscb(err);
                } else {
                    //console.log(data);
                    var recentBackupExists = false;
                    var mostRecentBackup = null;
                    var snapshots = data.Snapshots;
                    // console.log(snapshots);
                    for (var i = 0; i < snapshots.length; i++) {
                        var snapshot = snapshots[i];
                        var startTime = moment(snapshot.StartTime);
                        if (startTime.isAfter(backupMinimumDate)) {
                            recentBackupExists = true;
                        }
                        if (mostRecentBackup == null) {
                            mostRecentBackup = startTime;
                        } else {
                            if (startTime.isAfter(mostRecentBackup)) {
                                mostRecentBackup = startTime;
                            }
                        }
                    }
                    console.log('mostRecentBackup - ', mostRecentBackup, instance.InstanceId, recentBackupExists);
                    //  Volume could have been created after the last backup was preformed (less than 24 hours ago)
                    if (mostRecentBackup == null) {
                        var createTime = moment(volume.CreateTime);
                        var previous_time = moment().subtract(mins, 'minutes');
                        if (createTime.isAfter(previous_time)) {
                            console.log('Instance: ', instance.InstanceId, ' Volume: ', volume_id, ' was created after the last backups where done.');
                            dscb(null);
                            return;
                        }
                    }

                    if (recentBackupExists == false) {
                        if (mostRecentBackup == null) {
                            console.log('No backups for volume: ', volume_id, ' exist.');
                            var message = 'No backups for volume: ' + volume_id + ' exist.';
                            var msgData = {};
                            msgData.volumeId = volume_id;
                            msgData.InstanceId = instance.InstanceId;
                            msgData.correlation_id = instance.InstanceId;
                            msgData.scheduleInterval = mins;
                            msgData.latestBackup = 'None';
                            consolidated[instance.InstanceId]['VolumeIds'].push(volume_id);
                            consolidated[instance.InstanceId]['Event'] = 'BackupFailure';
                            // pushMessage(ErrorMessage, message, msgData, null);
                            console.log(consolidated[instance.InstanceId]);
                        } else {
                            console.log('A backup for volume: ', volume_id, ' does not exist within the last ', mins, ' mins.');
                            var message = 'A backup for volume: ' + volume_id + ' does not exist within the last ' + mins + ' mins.';
                            var msgData = {};
                            msgData.volumeId = volume_id;
                            msgData.InstanceId = instance.InstanceId;
                            msgData.correlation_id = instance.InstanceId;
                            msgData.scheduleInterval = mins;
                            msgData.latestBackup = mostRecentBackup;
                            consolidated[instance.InstanceId]['VolumeIds'].push(volume_id);
                            consolidated[instance.InstanceId]['Event'] = 'BackupFailure';
                            consolidated[instance.InstanceId]['LatestBackup'] = mostRecentBackup;
                            console.log(consolidated[instance.InstanceId]);
                            // pushMessage(ErrorMessage, message, msgData, null);
                        }
                    }
                    dscb(null);
                }
            });
        },
        function (err, result) {
            if (err) {
                console.log('Error during describeSnapshots: ', err.message);
                var message = 'An error occurred retrieving the snapshots for volume: ' + volume_id;
                var msgData = {};
                msgData.operation = 'describeSnapshots';
                msgData.requestParameters = describeSnapshots_params;
                pushMessage(ErrorMessage, message, msgData, err);
                callback(err);
            } else {
                callback(null);
            }
        });
}


function isBlank(str) {
    return (!str || /^\s*$/.test(str));
}

/*
*  Creates a CloudWatch event messages and pushes a message to the Backup SNS topic:
*
*  messageType - String - Warning, Information, Error, ...
*  subject - String - The SNS subject (intended to be the email subject)
*  messages - String - The message of what happened
*  data - json - additional data to support the message.  Probably Instance and Volume/Snapshot information
*/

function pushMessage(messageType, message, messageData, messageErr) {

    console.log(messageType, message, messageData, messageErr);

    var subject = 'Backup Health ' + messageType;

    messageData.region = process.env.AWS_REGION;
    var eventMsg = {};
    eventMsg.Trigger = {};
    eventMsg.Trigger.MetricName = messageType; // Information, Warning, Error
    eventMsg.Trigger.Dimensions = [
      {
        "name": "InstanceId",
        "value": messageData.InstanceId
      }

    ];

    eventMsg.AlarmName = 'BackupHealthService';
    eventMsg.NewStateReason = message;
    eventMsg.AWSAccountId = accountId;
    eventMsg.NewStateValue = 'ALARM';
    eventMsg.correlation_id = messageData.correlation_id;
    eventMsg.InstanceId = messageData.InstanceId;

    if (messageData != null) {
        eventMsg.eventData = messageData;
    } else {
        eventMsg.eventData = {};
    }
    if (messageErr != null) {
        eventMsg.err = messageErr;
    } else {
        eventMsg.err = {};
    }

    //  This is the message that is sent to the CloudWatch log:
    var messageStr = JSON.stringify(eventMsg, null, '\t');

    //  These are the messages that are sent to SNS.  One is an email messages and one
    //  is an HTTP messages that goes to ServiceNow:
    var text = 'The Backup Health Service encountered the following: \n' +
        message + '\n\n';
    if (messageErr != null) {
        text += 'AWS error message: \n';
        text += messageErr.message;
        text += '\n\n';
    }
    text += 'Request information:\n';
    text += JSON.stringify(messageData, null, '\t');
    text += '\n\n';
    if (messageErr != null) {
        text += 'Full error information:\n';
        text += JSON.stringify(messageErr, null, '\t');
    }
    var snsJson = {};
    if (messageErr != null) {
        snsJson.default = messageErr.message;
    } else {
        snsJson.default = JSON.stringify(messageData);
    }
    snsJson.email = text;
    snsJson.https = JSON.stringify(eventMsg, null, '\t');
    var snsJsonMsg = JSON.stringify(snsJson);
    // console.log('snsJsonMsg with both email and https is: ', snsJsonMsg);

    //  First, generate a CLoudWatch event.  This is formatted as json so the message can be
    //  pulled apart and filters applied:
    sendCW(messageStr);

    //  Send an SNS notification too:  Maybe don't send an SNS notification for Information message:
    if (messageType != InformationMessage) {
        sendSNS(subject, snsJsonMsg);
    }
}

function sendCW(message) {

    var tryNumber = 0;
    async.retry({
        times: 8,
        interval: function (retryCount) {
            return 10000 * retryCount + Math.floor((Math.random() * 10) + 1); //  10 seconds, 20 seconds, 40 seconds, etc.
        }
    },
        function (cwcb) {
            ++tryNumber;
            var describeParams = {
                logGroupName: BackupLogGroup,
                logStreamNamePrefix: BackupMessageStream
            };
            cwl.describeLogStreams(describeParams, function (err, data) {
                if (err) {
                    //console.log(err);
                    cwcb(err);
                } else {
                    //console.log(data);
                    var sequence = null;
                    var streams = data.logStreams;
                    for (var i = 0; i < streams.length; i++) {
                        var stream = streams[i];
                        var streamName = stream.logStreamName;
                        if (streamName == BackupMessageStream) {
                            sequence = stream.uploadSequenceToken;
                            break;
                        }
                    }
                    var epoch = moment().unix() * 1000;
                    var params = {
                        logEvents: [
                            {
                                message: message,
                                timestamp: epoch
                            }
                        ],
                        logGroupName: BackupLogGroup,
                        logStreamName: BackupMessageStream,
                        sequenceToken: sequence
                    };

                    cwl.putLogEvents(params, function (err, data) {
                        if (err) {
                            //console.log('Error during putLogEvents: ', err.message);
                            cwcb(err);
                        } else {
                            cwcb(null, data); //  No real result from this method to pass along...
                        }
                    });
                }
            });
        },
        function (err, result) {
            if (err) {
                console.log('Error sending event to CloudWatch: ', err.message);
            } else {
                //console.log('Message sent to CloudWatch: ', result);
            }
        });

}


function sendSNS(subject, message) {
    async.retry({
        errorFilter: function (err) {
            var retryable = err.retryable;
            return (retryable && retryable == true);
        },
        times: 5,
        interval: function (retryCount) {
            return 10000 * retryCount + Math.floor((Math.random() * 10) + 1); //  10 seconds, 20 seconds, 40 seconds, etc.
        }
    },
        function (snscb) {
            sns.listTopics({}, function (err, data) {
                if (err) {
                    //console.log('Error during listTopics: ', err.message);
                    snscb(err);
                } else {
                    //console.log(data);
                    var topicArn = null;
                    var topics = data.Topics;
                    for (var i = 0; i < topics.length; i++) {
                        var topic = topics[i];
                        var arn = topic.TopicArn;
                        if (arn.indexOf(BackupSNSTopic) > -1) {
                            topicArn = arn;
                            break;
                        }
                    }

                    if (topicArn != null) {
                        // console.log(message);
                        var snsParams = {
                            MessageStructure: 'json',
                            Message: message,
                            Subject: subject,
                            TopicArn: topicArn
                        };
                        sns.publish(snsParams, function (err, data) {
                            if (err) {
                                //console.log('Error during publish: ', err.message);
                                snscb(err);
                            } else {
                                //console.log(data);
                                snscb(null, data);
                            }
                        });
                    } else {
                        var noTopic = {};
                        noTopic.message = 'Topic: ' + BackupSNSTopic + ' was not found';
                        snscb(noTopic);
                    }
                }
            });
        },
        function (err, result) {
            if (err) {
                console.log('Error sending event to SNS: ', err.message);
            } else {
                //console.log('Message sent to CloudWatch: ', result);
            }
        });

}

function getParameter(parameterName, rCallBack) {

    // console.log('getting parameter for ' + parameterName + ' in parameter store');
  
    var params = { Name: parameterName, WithDecryption: true };
    async.retry({
      times: 5,
      interval: function (retryCount) {
          // Backoff interval between retries, 2 secs, 4 secs, 8 secs, 16 secs.
          let waitTime = 500 * Math.pow(2, retryCount);
          console.log('SSM Get Parameter: Exponential Backoff count:'+retryCount+ ', waitTime millisec:'+waitTime);
          
          return waitTime;
      }
    },
      function(rCallBack) {
            ssm.getParameter(params, function(err, data) {
            if (err) {
                console.log('issue with getParameter, error: ' + err);
                rCallBack(err);
            }
            else {
                if (data.Parameter.Value) {
                    incidentPriority = data.Parameter.Value;
                    return;
                }
                else {
                    rCallBack(new Error('Parameter ' + parameterName + ' not found'));
                }
            }
            });
        },
        function(error, result) {
            if (error) {
                rCallBack(error);
            } else {
                rCallBack(null,result);
            }
        });
  
  }

