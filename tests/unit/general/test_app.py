# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""S3 lib wrapper unit tests."""

import pytest

from paas_charm.app import generate_s3_env
from paas_charm.s3 import S3RelationData


@pytest.mark.parametrize(
    "relation_data, expected_env",
    [
        pytest.param(None, {}, id="No relation data"),
        pytest.param(
            S3RelationData.model_construct(
                access_key="access_key", secret_key="secret_key", bucket="bucket"
            ),
            {
                "S3_ACCESS_KEY": "access_key",
                "S3_SECRET_KEY": "secret_key",
                "S3_BUCKET": "bucket",
            },
            id="Minimum relation data",
        ),
        pytest.param(
            S3RelationData.model_construct(
                access_key="access_key",
                secret_key="secret_key",
                region="region",
                storage_class="standard",
                bucket="bucket",
                endpoint="endpoint",
                path="path",
                s3_api_version="version",
                s3_uri_style="url-style",
                tls_ca_chain=["---first---", "---second---"],
                attributes=["key1", "key2"],
            ),
            {
                "S3_ACCESS_KEY": "access_key",
                "S3_ADDRESSING_STYLE": "url-style",
                "S3_API_VERSION": "version",
                "S3_ATTRIBUTES": '["key1", "key2"]',
                "S3_BUCKET": "bucket",
                "S3_ENDPOINT": "endpoint",
                "S3_PATH": "path",
                "S3_REGION": "region",
                "S3_SECRET_KEY": "secret_key",
                "S3_STORAGE_CLASS": "standard",
                "S3_URI_STYLE": "url-style",
                "S3_TLS_CA_CHAIN": '["---first---", "---second---"]',
            },
            id="All relation data",
        ),
    ],
)
def test_s3_environ_mapper_generate_env(relation_data, expected_env):
    """
    arrange: given S3 relation data.
    act: when generate_s3_env method is called.
    assert: expected environment variables are generated.
    """
    assert generate_s3_env(relation_data) == expected_env
