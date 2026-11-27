# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the internal built-in relation classes."""

from unittest.mock import MagicMock

import pytest
from charmlibs.interfaces.smtp import SecretError, SmtpRelationData
from pydantic import ValidationError

from paas_charm.exceptions import RelationDataError
from paas_charm.s3 import InvalidS3RelationDataError, S3Relation
from paas_charm.saml import InvalidSAMLRelationDataError, SamlRelation
from paas_charm.smtp import InvalidSmtpRelationDataError, SmtpRelation
from paas_charm.tracing import InvalidTracingRelationDataError, TracingRelation
from paas_charm.valkey import (
    InvalidValkeyRelationDataError,
    ValkeyMultipleRelationsNotSupportedError,
    ValkeyRelation,
    ValkeyTLSNotSupportedError,
)


def _make_relation(charm_mock, relation_class, relation_name, optional=True):
    """Build a builtin relation instance with minimal mocking.

    Args:
        charm_mock: A mock charm to parent the relation.
        relation_class: The builtin relation class to instantiate.
        relation_name: The endpoint name.
        optional: Whether the endpoint is optional in metadata.

    Returns:
        An instantiated relation with _required and _context set.
    """
    relation = relation_class.__new__(relation_class)
    relation.relation_name = relation_name
    relation._charm = charm_mock
    relation._context = MagicMock()
    relation._required = not optional
    relation._requirer = None
    return relation


@pytest.mark.parametrize("optional", [True, False])
def test_valkey_relation_ensure_ready_with_data(optional):
    """
    arrange: A ValkeyRelation containing valkey data.
    act: Call ensure_ready.
    assert: Returns None without raising an exception.
    """
    charm_mock = MagicMock()
    relation = _make_relation(charm_mock, ValkeyRelation, "valkey", optional=optional)
    relation._requirer = MagicMock()
    assert relation.ensure_ready() is None
    relation._requirer.to_relation_data.assert_called_once_with()


@pytest.mark.parametrize("optional", [True, False])
def test_valkey_relation_not_ready_without_data(optional):
    """
    arrange: A configured ValkeyRelation with no Valkey data.
    act: Call ensure_ready.
    assert: Raises RelationDataError identifying the Valkey endpoint.
    """
    charm_mock = MagicMock()
    relation = _make_relation(charm_mock, ValkeyRelation, "valkey", optional=optional)
    relation._requirer = MagicMock()
    relation._requirer.to_relation_data.return_value = None
    with pytest.raises(RelationDataError, match="Valkey relation data is not ready") as exc:
        relation.ensure_ready()
    assert exc.value.relation == "valkey"


def test_valkey_relation_ensure_ready_when_not_configured():
    """
    arrange: A ValkeyRelation without a configured requirer.
    act: Call ensure_ready.
    assert: Returns None without raising an exception.
    """
    relation = _make_relation(MagicMock(), ValkeyRelation, "valkey")
    assert relation.ensure_ready() is None


@pytest.mark.parametrize(
    "error_type",
    [
        InvalidValkeyRelationDataError,
        ValkeyMultipleRelationsNotSupportedError,
        ValkeyTLSNotSupportedError,
    ],
)
def test_valkey_relation_ensure_ready_wraps_invalid_data(error_type):
    """
    arrange: A ValkeyRelation whose requirer rejects invalid or unsupported data.
    act: Call ensure_ready.
    assert: RelationDataError preserves the original message, endpoint, and cause.
    """
    relation = _make_relation(MagicMock(), ValkeyRelation, "valkey")
    relation._requirer = MagicMock()
    error = error_type("Invalid Valkey data")
    relation._requirer.to_relation_data.side_effect = error
    with pytest.raises(RelationDataError, match="Invalid Valkey data") as exc:
        relation.ensure_ready()
    assert type(exc.value) is RelationDataError
    assert str(exc.value) == str(error)
    assert exc.value.relation == "valkey"
    assert exc.value.__cause__ is error


@pytest.mark.parametrize("optional", [True, False])
def test_s3_relation_ensure_ready_with_data(optional):
    """
    arrange: An S3Relation containing S3 data.
    act: Call ensure_ready.
    assert: Returns None without raising an exception.
    """
    relation = _make_relation(MagicMock(), S3Relation, "s3", optional=optional)
    relation._requirer = MagicMock()
    assert relation.ensure_ready() is None
    relation._requirer.to_relation_data.assert_called_once_with()


@pytest.mark.parametrize("optional", [True, False])
def test_s3_relation_not_ready_without_data(optional):
    """
    arrange: A configured S3Relation with no S3 data.
    act: Call ensure_ready.
    assert: Raises RelationDataError identifying the S3 endpoint.
    """
    relation = _make_relation(MagicMock(), S3Relation, "s3", optional=optional)
    relation._requirer = MagicMock()
    relation._requirer.to_relation_data.return_value = None
    with pytest.raises(RelationDataError, match="S3 relation data is not ready") as exc:
        relation.ensure_ready()
    assert exc.value.relation == "s3"


def test_s3_relation_ensure_ready_when_not_configured():
    """
    arrange: An S3Relation without a configured requirer.
    act: Call ensure_ready.
    assert: Returns None without raising an exception.
    """
    relation = _make_relation(MagicMock(), S3Relation, "s3")
    assert relation.ensure_ready() is None


def test_s3_relation_ensure_ready_wraps_invalid_data():
    """
    arrange: An S3Relation whose requirer rejects invalid data.
    act: Call ensure_ready.
    assert: RelationDataError preserves the original message, endpoint, and cause.
    """
    relation = _make_relation(MagicMock(), S3Relation, "s3")
    relation._requirer = MagicMock()
    error = InvalidS3RelationDataError("Invalid S3 data")
    relation._requirer.to_relation_data.side_effect = error
    with pytest.raises(RelationDataError, match="Invalid S3 data") as exc:
        relation.ensure_ready()
    assert type(exc.value) is RelationDataError
    assert exc.value.relation == "s3"
    assert exc.value.__cause__ is error


@pytest.mark.parametrize("optional", [True, False])
def test_saml_relation_ensure_ready_with_data(optional):
    """
    arrange: A SamlRelation containing SAML data.
    act: Call ensure_ready.
    assert: Returns None without raising an exception.
    """
    relation = _make_relation(MagicMock(), SamlRelation, "saml", optional=optional)
    relation._requirer = MagicMock()
    assert relation.ensure_ready() is None
    relation._requirer.to_relation_data.assert_called_once_with()


@pytest.mark.parametrize("optional", [True, False])
def test_saml_relation_not_ready_without_data(optional):
    """
    arrange: A configured SamlRelation with no SAML data.
    act: Call ensure_ready.
    assert: Raises RelationDataError identifying the SAML endpoint.
    """
    relation = _make_relation(MagicMock(), SamlRelation, "saml", optional=optional)
    relation._requirer = MagicMock()
    relation._requirer.to_relation_data.return_value = None
    with pytest.raises(RelationDataError, match="SAML relation data is not ready") as exc:
        relation.ensure_ready()
    assert exc.value.relation == "saml"


def test_saml_relation_ensure_ready_when_not_configured():
    """
    arrange: A SamlRelation without a configured requirer.
    act: Call ensure_ready and gen_environment.
    assert: ensure_ready returns None and no environment is generated.
    """
    relation = _make_relation(MagicMock(), SamlRelation, "saml")
    assert relation.ensure_ready() is None
    assert relation.gen_environment() == {}


def test_saml_relation_ensure_ready_wraps_invalid_data():
    """
    arrange: A SamlRelation whose requirer rejects invalid data.
    act: Call ensure_ready.
    assert: RelationDataError preserves the original message, endpoint, and cause.
    """
    relation = _make_relation(MagicMock(), SamlRelation, "saml")
    relation._requirer = MagicMock()
    error = InvalidSAMLRelationDataError("Invalid SAML data")
    relation._requirer.to_relation_data.side_effect = error
    with pytest.raises(RelationDataError, match="Invalid SAML data") as exc:
        relation.ensure_ready()
    assert type(exc.value) is RelationDataError
    assert exc.value.relation == "saml"
    assert exc.value.__cause__ is error


@pytest.mark.parametrize("optional", [True, False])
def test_smtp_relation_ensure_ready_with_data(optional):
    """
    arrange: A SmtpRelation containing SMTP data.
    act: Call ensure_ready.
    assert: Returns None without raising an exception.
    """
    relation = _make_relation(MagicMock(), SmtpRelation, "smtp", optional=optional)
    relation._requirer = MagicMock()
    assert relation.ensure_ready() is None
    relation._requirer.get_relation_data.assert_called_once_with()


@pytest.mark.parametrize("optional", [True, False])
def test_smtp_relation_not_ready_without_data(optional):
    """
    arrange: A configured SmtpRelation with no SMTP data.
    act: Call ensure_ready.
    assert: Raises RelationDataError identifying the SMTP endpoint.
    """
    relation = _make_relation(MagicMock(), SmtpRelation, "smtp", optional=optional)
    relation._requirer = MagicMock()
    relation._requirer.get_relation_data.return_value = None
    with pytest.raises(RelationDataError, match="SMTP relation data is not ready") as exc:
        relation.ensure_ready()
    assert exc.value.relation == "smtp"


def test_smtp_relation_ensure_ready_when_not_configured():
    """
    arrange: A SmtpRelation without a configured requirer.
    act: Call ensure_ready and gen_environment.
    assert: ensure_ready returns None and no environment is generated.
    """
    relation = _make_relation(MagicMock(), SmtpRelation, "smtp")
    assert relation.ensure_ready() is None
    assert relation.gen_environment() == {}


def _smtp_validation_error() -> ValidationError:
    """Build a real SMTP ValidationError.

    Returns:
        The validation error raised for an invalid SMTP port.
    """
    try:
        SmtpRelationData(host="smtp.example.com", port="invalid")
    except ValidationError as exc:
        return exc
    raise AssertionError("SmtpRelationData accepted an invalid port")


@pytest.mark.parametrize(
    "error",
    [
        pytest.param(_smtp_validation_error(), id="validation error"),
        pytest.param(SecretError("Could not consume secret"), id="secret error"),
        pytest.param(ValueError("recipients must decode to a list"), id="value error"),
        pytest.param(TypeError("recipients must be a string"), id="type error"),
    ],
)
def test_smtp_relation_ensure_ready_wraps_invalid_data(error):
    """
    arrange: A SmtpRelation whose requirer raises an error for invalid data.
    act: Call ensure_ready and gen_environment.
    assert: ensure_ready raises RelationDataError for the SMTP endpoint, chained to the
        invalid data error, and gen_environment returns no environment.
    """
    relation = _make_relation(MagicMock(), SmtpRelation, "smtp")
    relation._requirer = MagicMock()
    relation._requirer.get_relation_data.side_effect = error
    with pytest.raises(RelationDataError, match="(?i)invalid smtp") as exc:
        relation.ensure_ready()
    assert type(exc.value) is RelationDataError
    assert exc.value.relation == "smtp"
    assert isinstance(exc.value.__cause__, InvalidSmtpRelationDataError)
    assert exc.value.__cause__.__cause__ is error
    assert relation.get_relation_data() is None
    assert relation.gen_environment() == {}


@pytest.mark.parametrize("optional", [True, False])
def test_tracing_relation_ensure_ready_with_data(optional):
    """
    arrange: A TracingRelation containing tracing data.
    act: Call ensure_ready.
    assert: Returns None without raising an exception.
    """
    relation = _make_relation(MagicMock(), TracingRelation, "tracing", optional=optional)
    relation._requirer = MagicMock()
    assert relation.ensure_ready() is None
    relation._requirer.to_relation_data.assert_called_once_with()


@pytest.mark.parametrize("optional", [True, False])
def test_tracing_relation_not_ready_without_data(optional):
    """
    arrange: A configured TracingRelation with no tracing data.
    act: Call ensure_ready.
    assert: Raises RelationDataError identifying the tracing endpoint.
    """
    relation = _make_relation(MagicMock(), TracingRelation, "tracing", optional=optional)
    relation._requirer = MagicMock()
    relation._requirer.to_relation_data.return_value = None
    with pytest.raises(RelationDataError, match="Tracing relation data is not ready") as exc:
        relation.ensure_ready()
    assert exc.value.relation == "tracing"


def test_tracing_relation_ensure_ready_when_not_configured():
    """
    arrange: A TracingRelation without a configured requirer.
    act: Call ensure_ready, is_ready and gen_environment.
    assert: ensure_ready returns None, is_ready is False, and no environment is generated.
    """
    relation = _make_relation(MagicMock(), TracingRelation, "tracing")
    assert relation.ensure_ready() is None
    assert relation.is_ready() is False
    assert relation.gen_environment() == {}


def test_tracing_relation_ensure_ready_wraps_invalid_data():
    """
    arrange: A TracingRelation whose requirer rejects invalid data.
    act: Call ensure_ready and gen_environment.
    assert: ensure_ready raises RelationDataError preserving the message, endpoint, and cause,
        while get_relation_data and gen_environment do not raise.
    """
    relation = _make_relation(MagicMock(), TracingRelation, "tracing")
    relation._requirer = MagicMock()
    error = InvalidTracingRelationDataError("Invalid tracing data")
    relation._requirer.to_relation_data.side_effect = error
    with pytest.raises(RelationDataError, match="Invalid tracing data") as exc:
        relation.ensure_ready()
    assert type(exc.value) is RelationDataError
    assert exc.value.relation == "tracing"
    assert exc.value.__cause__ is error
    assert relation.get_relation_data() is None
    assert relation.gen_environment() == {}
