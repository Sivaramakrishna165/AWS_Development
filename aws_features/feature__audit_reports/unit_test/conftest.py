import boto3
import os
import pytest

from moto import mock_s3, mock_sns, mock_dynamodb

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
def sns_client(aws_credentials):
    with mock_sns():
        conn = boto3.client("sns", region_name="us-east-1")
        yield conn        

@pytest.fixture
def ddb_resource(aws_credentials):
    with mock_dynamodb():
        conn = boto3.resource("dynamodb", region_name="us-east-1")
        yield conn                