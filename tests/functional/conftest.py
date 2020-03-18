from aws_lambda_context import LambdaContext
import pytest
from uuid import uuid4
import os


@pytest.fixture
def lambda_context():
    context = LambdaContext()
    context.function_name = "test"
    context.memory_limit_in_mb = 256
    context.invoked_function_arn = os.getenv(
        "AWS_LAMBDA_FUNCTION_INVOKED_ARN",
        "arn:aws:lambda:ap-southeast-2:123456789:function:test",
    )
    context.aws_request_id = str(uuid4())
    return context
