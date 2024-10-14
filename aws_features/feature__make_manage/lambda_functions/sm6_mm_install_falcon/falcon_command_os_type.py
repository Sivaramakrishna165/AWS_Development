ubuntu_falcon_command = '''
    echo "Start of Falcon sensor download"
    . /etc/os-release 
    VERSION=$VERSION_ID
    echo "version is $VERSION"
    VERSION_ID=`echo $VERSION | sed 's/\..*//'`
    echo "version id is $VERSION_ID"
    BUCKET="{}"
    echo "BUCKET is $BUCKET"
    FALCON=`aws s3 ls "s3://$BUCKET/deploy/externs/linux/ubuntu/$VERSION_ID/"  --recursive  | sort | tail -n 1 | sed 's/^[   ]*//' | cut -d"/" -f6-`
    echo "FALCON:$FALCON"
    if [[ -z $FALCON ]]; then
        echo "No $FALCON file found in $BUCKET/deploy/externs/linux/ubuntu/$VERSION_ID"
    else
        aws s3 cp "s3://$BUCKET/deploy/externs/linux/ubuntu/$VERSION_ID/$FALCON" /tmp/
        sudo apt install /tmp/$FALCON -y
    fi
'''
suse_falcon_command = '''
    echo "Start of Falcon sensor download"
    . /etc/os-release 
    VERSION_ID=$VERSION_ID
    echo "version is $VERSION_ID"
    VERSION_ID=$(cut -d'.' -f1 <<<$VERSION_ID)
    echo "version is $VERSION_ID"
    BUCKET="{}"
    echo "BUCKET is $BUCKET"
    FALCON=`/usr/local/bin/aws s3 ls "s3://$BUCKET/deploy/externs/linux/sles/$VERSION_ID/"  --recursive  | sort | tail -n 1 | sed 's/^[   ]*//' | cut -d"/" -f6-`
    echo "FALCON:$FALCON"
    if [[ -z $FALCON ]]; then
        echo "No $FALCON file found in $BUCKET/deploy/externs/linux/sles/$VERSION_ID"
    else
        aws s3 cp "s3://$BUCKET/deploy/externs/linux/sles/$VERSION_ID/$FALCON" /tmp/$FALCON
        if [[ $? -ne 0 ]]; then
            echo "Issue copying $FALCON file to host.";
        else
            echo "$FALCON file moved to instance."
            zypper -n install policycoreutils-python
            rpm -Uvh /tmp/$FALCON
        fi
    fi
'''
rhel_falcon_command = '''
    echo "Start of Falcon sensor download"
    . /etc/os-release 
    VERSION_ID=$VERSION_ID
    echo "version is $VERSION_ID"
    VERSION_ID=$(cut -d'.' -f1 <<<$VERSION_ID)
    echo "version is $VERSION_ID"
    BUCKET="{}"
    echo "BUCKET is $BUCKET"
    FALCON=`/usr/local/bin/aws s3 ls "s3://$BUCKET/deploy/externs/linux/rhel/$VERSION_ID/"  --recursive  | sort | tail -n 1 | sed 's/^[   ]*//' | cut -d"/" -f6-`
    echo "FALCON:$FALCON"
    if [[ -z $FALCON ]]; then
        echo "No $FALCON file found in $BUCKET/deploy/externs/linux/rhel/$VERSION_ID"
    else
        /usr/local/bin/aws s3 cp "s3://$BUCKET/deploy/externs/linux/rhel/$VERSION_ID/$FALCON" /tmp/$FALCON
        if [[ $? -ne 0 ]]; then
            echo "Issue copying $FALCON file to host.";
        else
            echo "$FALCON file moved to instance."
            rpm -Uvh /tmp/$FALCON
        fi
    fi
'''
oracle_falcon_command = '''
    echo "Start of Falcon sensor download"
    . /etc/os-release 
    VERSION_ID=$VERSION_ID
    echo "version is $VERSION_ID"
    VERSION_ID=$(cut -d'.' -f1 <<<$VERSION_ID)
    BUCKET="{}"
    echo "BUCKET is $BUCKET"
    FALCON=`aws s3 ls "s3://$BUCKET/deploy/externs/linux/oracle/$VERSION_ID/"  --recursive  | sort | tail -n 1 | sed 's/^[   ]*//' | cut -d"/" -f6-`
    echo "FALCON:$FALCON"
    if [[ -z $FALCON ]]; then
        echo "No $FALCON file found in $BUCKET/deploy/externs/linux/oracle/$VERSION_ID"
    else
        aws s3 cp "s3://$BUCKET/deploy/externs/linux/oracle/$VERSION_ID/$FALCON" /tmp/$FALCON
        if [[ $? -ne 0 ]]; then
            echo "Issue copying $FALCON file to host.";
        else
            echo "$FALCON file moved to instance."
            yum install -y libnl-1.1.4
            yum install policycoreutils-python -y
            rpm -Uvh /tmp/$FALCON
        fi
    fi
'''
amazonlinux_falcon_command = '''
    echo "Start of Falcon sensor download"
    if [ "true" ==  "true"  ]; then
       . /etc/os-release
       VERSION_ID=$(cut -d'.' -f1 <<<$VERSION_ID)
       echo "Version is $VERSION_ID   "
       OSARCH=`uname -m`
       echo "OSARCH: $OSARCH"
       if [ "$OSARCH" == "aarch64" ]; then   sub_folder="$VERSION_ID - arm64"
       elif [ "$OSARCH" == "x86_64" ]; then   sub_folder="$VERSION_ID"
       else  die "Could not identify OS architecture."
     fi
       echo "sub_folder is $sub_folder   "
       BUCKET="{}"
       echo "BUCKET is $BUCKET"
       FALCON=`aws s3 ls "s3://$BUCKET/deploy/externs/linux/amazon-linux/$sub_folder/"  --recursive  | sort | tail -n 1 | sed 's/^[   ]*//' | cut -d"/" -f6-`
       echo "FALCON:$FALCON"
       if [[ -z $FALCON ]]; then
            echo "No $FALCON file found in $BUCKET/deploy/externs/linux/amazon-linux/$sub_folder"
        else
            aws s3 cp "s3://$BUCKET/deploy/externs/linux/amazon-linux/$sub_folder/$FALCON" /tmp/
            if [[ $? -ne 0 ]]; then
                echo "Issue copying $FALCON file to host.";
            else
                echo "$FALCON file moved to instance."
                yum install -y libnl-1.1.4
                yum install policycoreutils-python -y
                rpm -Uvh /tmp/$FALCON
            fi
        fi
    else
     echo "ApplyEndpointProtection is set to False"
    fi
'''
windows_falcon_command = """# Download and install Falcon host if ApplyEndPointProtection is enabled 
Set-Variable -Name "crowdStrikeExe" -Value "WindowsSensor.exe"
Get-Variable -Name "crowdStrikeExe"
Set-Variable -Name "BUCKET" -Value "{}"
Get-Variable -Name "BUCKET"
Set-Variable -Name "REGIONNAME" -Value "{}"
Get-Variable -Name "REGIONNAME"
Read-S3Object -BucketName $BUCKET -key deploy/externs/windows/$crowdStrikeExe -Region $REGIONNAME -File c:\Temp\$crowdStrikeExe 
cd c:\Temp
Set-Variable -Name  "installer" -Value ".\$crowdStrikeExe /install /quiet /norestart CID={}"
Get-Variable -Name "installer"
Invoke-Expression -Command $installer
Get-Service | findstr /i /r "Running.*CrowdStrike" """