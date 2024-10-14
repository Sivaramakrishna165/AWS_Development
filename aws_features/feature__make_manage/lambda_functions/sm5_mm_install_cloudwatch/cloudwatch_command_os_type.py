ubuntu_cloudwatch_command = [
    'sudo wget https://s3.{r}.amazonaws.com/amazoncloudwatch-agent-{r}/ubuntu/{a}/latest/amazon-cloudwatch-agent.deb',
    'sudo dpkg -i -E ./amazon-cloudwatch-agent.deb',
    '/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -c ssm:/DXC/AWS-CWAgentConfig -s'
]

suse_cloudwatch_command = [
    'sudo rpm -Uvh https://s3.{r}.amazonaws.com/amazoncloudwatch-agent-{r}/suse/{a}/latest/amazon-cloudwatch-agent.rpm',
    'sudo rpm -U ./amazon-cloudwatch-agent.rpm',
    '/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -c ssm:/DXC/AWS-CWAgentConfig -s'
]

rhel_cloudwatch_command = [
    'sudo rpm -Uvh https://s3.{r}.amazonaws.com/amazoncloudwatch-agent-{r}/redhat/{a}/latest/amazon-cloudwatch-agent.rpm',
    'sudo rpm -U ./amazon-cloudwatch-agent.rpm',
    '/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -c ssm:/DXC/AWS-CWAgentConfig -s'
]

oracle_cloudwatch_command = [
    'sudo rpm -Uvh https://s3.{r}.amazonaws.com/amazoncloudwatch-agent-{r}/oracle_linux/{a}/latest/amazon-cloudwatch-agent.rpm',
    'sudo rpm -U ./amazon-cloudwatch-agent.rpm',
    '/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -c ssm:/DXC/AWS-CWAgentConfig -s'
]

amazonlinux2_cloudwatch_command = [
    'sudo rpm -Uvh https://s3.{r}.amazonaws.com/amazoncloudwatch-agent-{r}/amazon_linux/{a}/latest/amazon-cloudwatch-agent.rpm',
    'sudo rpm -U ./amazon-cloudwatch-agent.rpm',
    '/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -c ssm:/DXC/AWS-CWAgentConfig -s'
]

windows_cloudwatch_command1 = [
    'Invoke-WebRequest https://s3.{r}.amazonaws.com/amazoncloudwatch-agent-{r}/windows/{a}/latest/amazon-cloudwatch-agent.msi  -OutFile c:\\Users\Administrator\Desktop\\amazon-cloudwatch-agent.msi',
    'msiexec /i c:\\Users\Administrator\Desktop\\amazon-cloudwatch-agent.msi'
]

windows_cloudwatch_command2 = [
    '& "C:\\Program Files\\Amazon\\AmazonCloudWatchAgent\\amazon-cloudwatch-agent-ctl.ps1" -a fetch-config -m ec2 -s -c ssm:/DXC/AWS-CWAgentWinConfig'
]