# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""S3 lib wrapper unit tests."""

from unittest.mock import MagicMock

import pytest

from paas_charm.s3 import InvalidS3RelationDataError, PaaSS3RelationData, PaaSS3Requirer


@pytest.mark.parametrize(
    "relation_data, expected",
    [
        pytest.param(None, None, id="No data"),
        pytest.param({}, None, id="Empty data"),
        pytest.param(
            {
                "access-key": "access_key",
                "secret-key": "secret_key",
                "bucket": "bucket",
            },
            PaaSS3RelationData.model_construct(
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
            PaaSS3RelationData.model_construct(
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
def test_requirer_to_relation_data(monkeypatch, relation_data, expected):
    """
    arrange: given s3 relation data.
    act: when to_relation_data is called.
    assert: expected relation data is returned.
    """
    s3_requirer = PaaSS3Requirer(MagicMock(), "test-s3-integration", "test-bucket")
    monkeypatch.setattr(
        s3_requirer, "get_s3_connection_info", MagicMock(return_value=relation_data)
    )

    assert s3_requirer.to_relation_data() == expected


@pytest.mark.parametrize(
    "relation_data",
    [
        pytest.param({"invalid": "data"}, id="Invalid data"),
        pytest.param({"secret-key": "key", "bucket": "bucket"}, id="Missing data (access-key)"),
        pytest.param({"access-key": "key", "bucket": "bucket"}, id="Missing data (secret-key)"),
        pytest.param({"access-key": "key", "secret-key": "key"}, id="Missing data (bucket)"),
    ],
)
def test_requirer_to_validation_error(monkeypatch, relation_data):
    """
    arrange: given incomplete/invalid relation data.
    act: when to_relation_data is called.
    assert: InvalidS3RelationDataError is raised.
    """
    s3_requirer = PaaSS3Requirer(MagicMock(), "test-s3-integration", "test-bucket")
    monkeypatch.setattr(
        s3_requirer, "get_s3_connection_info", MagicMock(return_value=relation_data)
    )

    with pytest.raises(InvalidS3RelationDataError) as exc:
        s3_requirer.to_relation_data()

    assert "S3" in str(exc.value)
