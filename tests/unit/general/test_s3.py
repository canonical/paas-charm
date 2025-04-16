# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""S3 lib wrapper unit tests."""

from unittest.mock import MagicMock

import pytest

from paas_charm.s3 import PaaSS3Requirer, S3RelationData


@pytest.mark.parametrize(
    "relation_data, expected",
    [
        pytest.param(None, None, id="No data"),
        pytest.param(
            {
                "access-key": "access_key",
                "secret-key": "secret_key",
                "bucket": "bucket",
            },
            S3RelationData.model_construct(
                access_key="access_key",
                secret_key="secret_key",
                bucket="bucket",
            ),
            id="Minimum data",
        ),
        pytest.param(
            {
                "access-key": "access_key",
                "secret-key": "secret_key",
                "region": "region",
                "storage-class": "GLACIER",
                "bucket": "bucket",
                "endpoint": "https://s3.example.com",
                "path": "/path/subpath/",
                "s3-api-version": "s3v4",
                "s3-uri-style": "host",
                "tls-ca-chain": [
                    "-----BEGIN CERTIFICATE-----\nTHE FIRST LONG CERTIFICATE\n-----END CERTIFICATE-----",
                    "-----BEGIN CERTIFICATE-----\nTHE SECOND LONG CERTIFICATE\n-----END CERTIFICATE-----",
                ],
                "attributes": [
                    "header1:value1",
                    "header2:value2",
                ],
            },
            S3RelationData.model_construct(
                access_key="access_key",
                secret_key="secret_key",
                region="region",
                storage_class="GLACIER",
                bucket="bucket",
                endpoint="https://s3.example.com",
                path="/path/subpath/",
                s3_api_version="s3v4",
                s3_uri_style="host",
                tls_ca_chain=(
                    ca_chain := [
                        "-----BEGIN CERTIFICATE-----\nTHE FIRST LONG CERTIFICATE\n-----END CERTIFICATE-----",
                        "-----BEGIN CERTIFICATE-----\nTHE SECOND LONG CERTIFICATE\n-----END CERTIFICATE-----",
                    ]
                ),
                attributes=(
                    attributes := [
                        "header1:value1",
                        "header2:value2",
                    ]
                ),
            ),
            id="Maximum data",
        ),
    ],
)
def test_generate_relation_parameters(monkeypatch, relation_data, expected):
    s3_requirer = PaaSS3Requirer(MagicMock(), "test-s3-integration", "test-bucket")
    monkeypatch.setattr(
        s3_requirer, "get_s3_connection_info", MagicMock(return_value=relation_data)
    )

    assert s3_requirer.to_relation_data() == expected
