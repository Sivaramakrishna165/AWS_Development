import boto3
import os
import pytest

from moto import mock_s3, mock_sqs, mock_ssm, mock_cloudformation


@pytest.fixture
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"


@pytest.fixture
def s3_client(aws_credentials):
    with mock_s3():
        conn = boto3.client("s3", region_name="us-east-1")
        yield conn

@pytest.fixture
def ssm_client(aws_credentials):
    with mock_ssm():
        conn = boto3.client("ssm", region_name="us-east-1")
        yield conn

@pytest.fixture
def cft_client(aws_credentials):
    with mock_cloudformation():
        conn = boto3.client("cloudformation", region_name="us-east-1")
        yield conn        

@pytest.fixture
def sqs_client(aws_credentials):
    with mock_sqs():
        conn = boto3.client("sqs", region_name="us-east-1")
        yield conn

@pytest.fixture
def ec2_client(aws_credentials):
    with mock_ec2():
        conn = boto3.client("ec2", region_name="us-east-1")
        yield conn

@pytest.fixture
def ec2_resource(aws_credentials):
    with mock_ec2():
        conn = boto3.resource("ec2", region_name="us-east-1")
        yield conn