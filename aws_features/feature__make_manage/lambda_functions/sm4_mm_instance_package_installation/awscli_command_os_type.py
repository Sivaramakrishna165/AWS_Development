ubuntu_awscli_command = '''
    sudo -i
    apt-get install -y -q python3
    apt-get install -y -q unzip
    if [ ! -d /awspe/awscliv2 ]; then
        mkdir -p /awspe/awscliv2
        chmod 777 /awspe/awscliv2
        echo "directory created"
        echo $?
        cd /awspe/awscliv2
        echo $?
        echo "directory changed to awscliv2"
        echo $?
        curl "https://awscli.amazonaws.com/awscli-exe-linux-{}.zip" -o "awscliv2.zip" >> /awspe/awscliv2/awscliv2.log
        echo $?
        echo "download completed"
        echo $?
        unzip -o -q awscliv2.zip >> /awspe/awscliv2/awscliv2.log
        echo $?
        echo "unzip completed"
        echo $?
        sudo ./aws/install --update >> /awspe/awscliv2/awscliv2.log
        echo $?
        echo "AWSCLIV2 Installed"
        echo $?
        ln -s /usr/local/bin/aws /usr/bin/aws
    fi
'''
suse_awscli_command = '''
    sudo -i
    yum install -y -q python3
    yum install -y -q unzip
    if [ ! -d /awspe/awscliv2 ]; then
        mkdir -p /awspe/awscliv2
        chmod 777 /awspe/awscliv2
        echo "directory created"
        echo $?
        cd /awspe/awscliv2
        echo $?
        echo "directory changed to awscliv2"
        echo $?
        curl "https://awscli.amazonaws.com/awscli-exe-linux-{}.zip" -o "awscliv2.zip" >> /awspe/awscliv2/awscliv2.log
        echo $?
        echo "download completed"
        echo $?
        unzip -o -q awscliv2.zip >> /awspe/awscliv2/awscliv2.log
        echo $?
        echo "unzip completed"
        echo $?
        sudo ./aws/install --update >> /awspe/awscliv2/awscliv2.log
        echo $?
        echo "AWSCLIV2 Installed"
        echo $?
        ln -s /usr/local/bin/aws /usr/bin/aws
    fi
'''
rhel_awscli_command = '''
    sudo -i
    yum install -y -q python3
    yum install -y -q unzip
    if [ ! -d /awspe/awscliv2 ]; then
        mkdir -p /awspe/awscliv2
        chmod 777 /awspe/awscliv2
        echo "directory created"
        echo $?
        cd /awspe/awscliv2
        echo $?
        echo "directory changed to awscliv2"
        echo $?
        curl "https://awscli.amazonaws.com/awscli-exe-linux-{}.zip" -o "awscliv2.zip" >> /awspe/awscliv2/awscliv2.log
        echo $?
        echo "download completed"
        echo $?
        unzip -o -q awscliv2.zip >> /awspe/awscliv2/awscliv2.log
        echo $?
        echo "unzip completed"
        echo $?
        sudo ./aws/install -i /usr/local/aws-cli -b /usr/local/bin --update >> /awspe/awscliv2/awscliv2.log
        echo $?
        echo "AWSCLIV2 Installed"
        echo $?
        ln -s /usr/local/bin/aws /usr/bin/aws
    fi
'''
oracle_awscli_command = '''
    sudo -i
    yum install -y -q python3
    yum install -y -q unzip
    if [ ! -d /awspe/awscliv2 ]; then
        mkdir -p /awspe/awscliv2
        chmod 777 /awspe/awscliv2
        echo "directory created"
        echo $?
        cd /awspe/awscliv2
        echo $?
        echo "directory changed to awscliv2"
        echo $?
        curl "https://awscli.amazonaws.com/awscli-exe-linux-{}.zip" -o "awscliv2.zip" >> /awspe/awscliv2/awscliv2.log
        echo $?
        echo "download completed"
        echo $?
        unzip -o -q awscliv2.zip >> /awspe/awscliv2/awscliv2.log
        echo $?
        echo "unzip completed"
        echo $?
        sudo ./aws/install --update >> /awspe/awscliv2/awscliv2.log
        echo $?
        echo "AWSCLIV2 Installed"
        echo $?
        ln -s /usr/local/bin/aws /usr/bin/aws
    fi
'''
amazonlinux_awscli_command = '''
    sudo -i
    yum install -y -q python3
    yum install -y -q unzip
    if [ ! -d /awspe/awscliv2 ]; then
        mkdir -p /awspe/awscliv2
        chmod 777 /awspe/awscliv2
        echo "directory created"
        echo $?
        cd /awspe/awscliv2
        echo $?
        echo "directory changed to awscliv2"
        echo $?
        curl "https://awscli.amazonaws.com/awscli-exe-linux-{}.zip" -o "awscliv2.zip" >> /awspe/awscliv2/awscliv2.log
        echo $?
        echo "download completed"
        echo $?
        unzip -o -q awscliv2.zip >> /awspe/awscliv2/awscliv2.log
        echo $?
        echo "unzip completed"
        echo $?
        sudo ./aws/install --update >> /awspe/awscliv2/awscliv2.log
        echo $?
        echo "AWSCLIV2 Installed"
        echo $?
        ln -s /usr/local/bin/aws /usr/bin/aws
    fi
'''
windows_awscli_command = """
    $progressPreference = 'silentlyContinue'
    start-Process -FilePath "msiexec.exe" -ArgumentList '/i https://awscli.amazonaws.com/AWSCLIV2.msi /quiet /norestart /l C:\\Users\Administrator\Desktop\installlog.txt'
    Write-Host "Done install"
"""
