common_ssm_command = '''Content-Type: multipart/mixed; boundary="//"
MIME-Version: 1.0

--//
Content-Type: text/cloud-config; charset="us-ascii"
MIME-Version: 1.0
Content-Transfer-Encoding: 7bit
Content-Disposition: attachment; filename="cloud-config.txt"

#cloud-config
cloud_final_modules:
- [scripts-user, always]

--//
Content-Type: text/x-shellscript; charset="us-ascii"
MIME-Version: 1.0
Content-Transfer-Encoding: 7bit
Content-Disposition: attachment; filename="userdata.txt"
'''

amzlinux2_ssm_command = '''
#!/bin/bash
cd /tmp
echo "installation started"
sudo yum install -y https://s3.{}.amazonaws.com/amazon-ssm-{}/latest/linux_{}/amazon-ssm-agent.rpm
echo "installation completed"
sudo systemctl enable amazon-ssm-agent
echo "enabling done"
sudo systemctl start amazon-ssm-agent
echo "start done"
--//--
'''

amzlinux_ssm_command = '''
#!/bin/bash
cd /tmp
echo "installation started"
sudo yum install -y https://s3.{}.amazonaws.com/amazon-ssm-{}/latest/linux_{}/amazon-ssm-agent.rpm
sudo start amazon-ssm-agent
echo "start done"
--//--
'''

rhel_ssm_command = '''
#!/bin/bash
echo "installation started"
sudo yum install -y https://s3.{}.amazonaws.com/amazon-ssm-{}/latest/linux_{}/amazon-ssm-agent.rpm
sudo systemctl enable amazon-ssm-agent
sudo systemctl start amazon-ssm-agent
echo "start done"
--//--
'''

ubuntu_ssm_command = '''
#!/bin/bash
mkdir /tmp/ssm
cd /tmp/ssm
echo "installation started"
sudo wget https://s3.{}.amazonaws.com/amazon-ssm-{}/latest/debian_{}/amazon-ssm-agent.deb
sudo dpkg -i amazon-ssm-agent.deb
sudo systemctl enable amazon-ssm-agent
sudo snap start amazon-ssm-agent
echo "start done"
--//--
'''

suse_ssm_command = '''
#!/bin/bash
mkdir /tmp/ssm
cd /tmp/ssm
echo "installation started"
sudo wget https://s3.{}.amazonaws.com/amazon-ssm-{}/latest/linux_{}/amazon-ssm-agent.rpm
sudo rpm --install amazon-ssm-agent.rpm
sudo systemctl enable amazon-ssm-agent
sudo systemctl start amazon-ssm-agent
echo "start done"
--//--
'''

windows_ssm_command = '''
<powershell>
$progressPreference = 'silentlyContinue'
Invoke-WebRequest https://s3.amazonaws.com/ec2-downloads-windows/SSMAgent/latest/windows_amd64/AmazonSSMAgentSetup.exe -OutFile c:\\Users\Administrator\Desktop\SSMAgent_latest.exe
Start-Process -FilePath c:\\Users\Administrator\Desktop\SSMAgent_latest.exe -ArgumentList "/S"
</powershell>
<persist>true</persist>
--//--'''

oracle_ssm_command ='''
#!/bin/bash
echo "installation started"
sudo yum install -y https://s3.{}.amazonaws.com/amazon-ssm-{}/latest/linux_{}/amazon-ssm-agent.rpm
sudo systemctl enable amazon-ssm-agent
sudo systemctl start amazon-ssm-agent
echo "start done"
--//--
'''
