# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""OpenSearch unit tests."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from charms.data_platform_libs.v0.data_interfaces import OpenSearchRequires
from ops import ModelError, RelationMeta, RelationRole, SecretNotFoundError

from paas_charm.exceptions import InvalidRelationInterfaceError, RelationDataError
from paas_charm.opensearch import (
    OPENSEARCH_RELATION_NAME,
    OpenSearchRelation,
    PaaSOpenSearchRelationData,
)

RELATION_ID = 1
ENDPOINTS = "10.1.1.1:9200,10.1.1.2:9200"
TLS_CA = (
    "-----BEGIN CERTIFICATE-----\nTHE INTERMEDIATE CA CERTIFICATE\n-----END CERTIFICATE-----\n"
    "-----BEGIN CERTIFICATE-----\nTHE ROOT CA CERTIFICATE\n-----END CERTIFICATE-----"
)


def _without(data, *keys):
    """Return a copy of a mapping without the given keys."""
    return {key: value for key, value in data.items() if key not in keys}


PROVIDER_RELATION_DATA_TLS_CA = {
    "endpoints": ENDPOINTS,
    "username": "opensearch-client_1",
    "password": "test-password",
    "tls-ca": TLS_CA,
    "index": "test-index",
    "version": "2.19.0",
}
PROVIDER_RELATION_DATA_MISSING_INDEX = _without(PROVIDER_RELATION_DATA_TLS_CA, "index")
PROVIDER_RELATION_DATA_MISSING_VERSION = _without(PROVIDER_RELATION_DATA_TLS_CA, "version")
# Fetching the relation data without a list of fields returns these fields too.
PROVIDER_RELATION_DATA_EXTRA_KEYS = {
    **PROVIDER_RELATION_DATA_TLS_CA,
    "tls": "True",
    "data": '{"index": "test-index", "extra-user-roles": "admin"}',
}
PROVIDER_RELATION_DATA_MISSING_ENDPOINTS = _without(PROVIDER_RELATION_DATA_TLS_CA, "endpoints")
PROVIDER_RELATION_DATA_MISSING_USERNAME = _without(PROVIDER_RELATION_DATA_TLS_CA, "username")
PROVIDER_RELATION_DATA_MISSING_PASSWORD = _without(PROVIDER_RELATION_DATA_TLS_CA, "password")
PROVIDER_RELATION_DATA_MISSING_TLS_CA = _without(PROVIDER_RELATION_DATA_TLS_CA, "tls-ca")
# The provider shares the CA in "tls-ca", so a "tls_ca" field isn't read.
PROVIDER_RELATION_DATA_TLS_CA_UNDERSCORE = {
    **PROVIDER_RELATION_DATA_MISSING_TLS_CA,
    "tls_ca": TLS_CA,
}
# The provider can share the index and the endpoints before the credentials and the CA.
PROVIDER_RELATION_DATA_ENDPOINTS_ONLY = {"endpoints": ENDPOINTS, "index": "test-index"}

EXPECTED_ENV = {
    "OPENSEARCH_ENDPOINTS": ENDPOINTS,
    "OPENSEARCH_USERNAME": "opensearch-client_1",
    "OPENSEARCH_PASSWORD": "test-password",
    "OPENSEARCH_TLS_CA": TLS_CA,
    "OPENSEARCH_INDEX": "test-index",
    "OPENSEARCH_VERSION": "2.19.0",
}

READY_RELATION_DATA_AND_ENV = [
    pytest.param(PROVIDER_RELATION_DATA_TLS_CA, EXPECTED_ENV, id="complete data"),
    pytest.param(
        PROVIDER_RELATION_DATA_MISSING_INDEX,
        _without(EXPECTED_ENV, "OPENSEARCH_INDEX"),
        id="missing index",
    ),
    pytest.param(
        PROVIDER_RELATION_DATA_MISSING_VERSION,
        _without(EXPECTED_ENV, "OPENSEARCH_VERSION"),
        id="missing version",
    ),
    pytest.param(PROVIDER_RELATION_DATA_EXTRA_KEYS, EXPECTED_ENV, id="extra keys"),
]
READY_RELATION_DATA = [
    pytest.param(param.values[0], id=param.id) for param in READY_RELATION_DATA_AND_ENV
]
NOT_READY_RELATION_DATABAGS = [
    pytest.param({RELATION_ID: PROVIDER_RELATION_DATA_MISSING_ENDPOINTS}, id="missing endpoints"),
    pytest.param({RELATION_ID: PROVIDER_RELATION_DATA_MISSING_USERNAME}, id="missing username"),
    pytest.param({RELATION_ID: PROVIDER_RELATION_DATA_MISSING_PASSWORD}, id="missing password"),
    pytest.param({RELATION_ID: PROVIDER_RELATION_DATA_MISSING_TLS_CA}, id="missing tls-ca"),
    pytest.param(
        {RELATION_ID: PROVIDER_RELATION_DATA_TLS_CA_UNDERSCORE}, id="tls_ca instead of tls-ca"
    ),
    pytest.param({RELATION_ID: PROVIDER_RELATION_DATA_ENDPOINTS_ONLY}, id="endpoints only"),
    pytest.param({RELATION_ID: {}}, id="empty provider relation data"),
    pytest.param({}, id="no relation"),
]


def _make_requirer(relation_databags, error=None):
    """Build an OpenSearchRequires mock that serves the given provider databags.

    Args:
        relation_databags: The provider databags, indexed by relation ID.
        error: The exception raised when fetching the relation data, if any.

    Returns:
        A requirer mock whose fetch_relation_data behaves like the library one.
    """

    def fetch_relation_data(relation_ids=None, fields=None, relation_name=None):
        if relation_name not in (None, OPENSEARCH_RELATION_NAME):
            return {}
        return {
            relation_id: {
                key: value for key, value in databag.items() if not fields or key in fields
            }
            for relation_id, databag in relation_databags.items()
            if not relation_ids or relation_id in relation_ids
        }

    requirer = MagicMock(spec=OpenSearchRequires)
    requirer.relations = [MagicMock(id=relation_id) for relation_id in relation_databags]
    requirer.fetch_relation_data.side_effect = error or fetch_relation_data
    return requirer


def _make_charm(interface="opensearch_client"):
    """Build a charm mock that only declares the opensearch endpoint.

    Args:
        interface: The interface of the opensearch endpoint.

    Returns:
        A charm mock whose metadata and relation events only know the opensearch endpoint.
    """
    charm = MagicMock()
    charm.framework.meta.requires = {
        OPENSEARCH_RELATION_NAME: RelationMeta(
            role=RelationRole.requires,
            relation_name=OPENSEARCH_RELATION_NAME,
            raw={"interface": interface, "limit": 1},
        )
    }
    charm.on.__getitem__.side_effect = {OPENSEARCH_RELATION_NAME: MagicMock()}.__getitem__
    return charm


def _make_relation(requirer=None, charm=None):
    """Build an OpenSearchRelation without the ops framework.

    Args:
        requirer: The requirer of the relation, None if it is not configured.
        charm: The parent charm, a mock by default.

    Returns:
        The relation, as the framework creates it before calling setup.
    """
    relation = OpenSearchRelation.__new__(OpenSearchRelation)
    relation._charm = charm or MagicMock()
    relation._context = MagicMock()
    relation._required = False
    relation._requirer = requirer
    return relation


def test_successful_setup(monkeypatch):
    """
    arrange: given OpenSearchRelation with valid configs and interface name.
    act: when setup is called.
    assert: None is returned and _requirer is set.
    """
    paas_config = SimpleNamespace(
        opensearch=SimpleNamespace(index="test-index", extra_user_roles="admin")
    )
    monkeypatch.setattr(
        "paas_charm.opensearch.read_paas_config", MagicMock(return_value=paas_config)
    )
    requires_class = MagicMock()
    monkeypatch.setattr("paas_charm.opensearch.OpenSearchRequires", requires_class)
    relation = _make_relation(charm=_make_charm())

    assert relation.setup(MagicMock()) is None

    requires_class.assert_called_once()
    assert relation._requirer is requires_class.return_value


def test_setup_invalid_relation_interface():
    """
    arrange: given OpenSearchRelation on an endpoint that doesn't use opensearch_client.
    act: when setup is called.
    assert: InvalidRelationInterfaceError is raised.
    """
    relation = _make_relation(charm=_make_charm(interface="opensearch-client"))

    with pytest.raises(
        InvalidRelationInterfaceError,
        match="Built-in OpenSearch relation interface is not 'opensearch_client'",
    ):
        relation.setup(MagicMock())


# TODO: Implement a test when no `opensearch` section appears in `paas-config.yaml`
# Wait until I know how setup read the config.


@pytest.mark.parametrize("relation_data", READY_RELATION_DATA)
def test_successful_relation_data(relation_data):
    """
    arrange: given OpenSearchRelation with a valid databag.
    act: when _relation_data is called.
    assert: a PaaSOpenSearchRelationData with identical values is returned.
    """
    relation = _make_relation(requirer=_make_requirer({RELATION_ID: relation_data}))

    assert relation._relation_data() == PaaSOpenSearchRelationData.model_validate(relation_data)


@pytest.mark.parametrize("relation_databags", NOT_READY_RELATION_DATABAGS)
def test_missing_relation_data(relation_databags):
    """
    arrange: given OpenSearchRelation with a databag missing a required field.
    act: when _relation_data is called.
    assert: None is returned.
    """
    relation = _make_relation(requirer=_make_requirer(relation_databags))

    assert relation._relation_data() is None


@pytest.mark.parametrize(
    "error",
    [
        pytest.param(SecretNotFoundError("secret not found"), id="secret not found"),
        pytest.param(ModelError("ERROR permission denied"), id="permission denied"),
    ],
)
def test_relation_data_when_secret_not_found(error):
    """
    arrange: given a requirer that can't find or read the secrets of the relation.
    act: when _relation_data is called.
    assert: RelationDataError is raised with proper message, relation name and cause.
    """
    relation = _make_relation(
        requirer=_make_requirer({RELATION_ID: PROVIDER_RELATION_DATA_TLS_CA}, error=error)
    )

    with pytest.raises(RelationDataError, match="OpenSearch") as exc:
        relation._relation_data()

    assert exc.value.relation == OPENSEARCH_RELATION_NAME
    assert exc.value.__cause__ is error


def test_relation_data_when_multiple_relations():
    """
    arrange: given a requirer returning databags for more than one relation.
    act: when _relation_data is called.
    assert: RelationDataError is raised with proper message and relation name.
    """
    relation = _make_relation(
        requirer=_make_requirer(
            {1: PROVIDER_RELATION_DATA_TLS_CA, 2: PROVIDER_RELATION_DATA_TLS_CA}
        )
    )

    with pytest.raises(
        RelationDataError, match="Multiple OpenSearch relations are not supported"
    ) as exc:
        relation._relation_data()

    assert exc.value.relation == OPENSEARCH_RELATION_NAME


def test_relation_data_when_not_configured():
    """
    arrange: given OpenSearchRelation without a _requirer.
    act: when _relation_data is called.
    assert: None is returned.
    """
    relation = _make_relation()

    assert relation._relation_data() is None


@pytest.mark.parametrize("relation_data", READY_RELATION_DATA)
def test_ensure_ready_when_ready(relation_data):
    """
    arrange: given OpenSearchRelation with a valid databag.
    act: when ensure_ready is called.
    assert: None is returned.
    """
    relation = _make_relation(requirer=_make_requirer({RELATION_ID: relation_data}))

    assert relation.ensure_ready() is None


def test_ensure_ready_when_no_requirer():
    """
    arrange: given OpenSearchRelation without a _requirer.
    act: when ensure_ready is called.
    assert: RelationDataError is raised with proper message and relation name.
    """
    relation = _make_relation()

    with pytest.raises(RelationDataError, match="OpenSearch relation data is not ready") as exc:
        relation.ensure_ready()

    assert exc.value.relation == OPENSEARCH_RELATION_NAME


@pytest.mark.parametrize("relation_databags", NOT_READY_RELATION_DATABAGS)
def test_ensure_ready_when_not_ready(relation_databags):
    """
    arrange: given OpenSearchRelation with a databag missing a required field.
    act: when ensure_ready is called.
    assert: RelationDataError is raised with proper message and relation name.
    """
    relation = _make_relation(requirer=_make_requirer(relation_databags))

    with pytest.raises(RelationDataError, match="OpenSearch relation data is not ready") as exc:
        relation.ensure_ready()

    assert exc.value.relation == OPENSEARCH_RELATION_NAME


@pytest.mark.parametrize(
    "relation_databags, error",
    [
        pytest.param(
            {RELATION_ID: PROVIDER_RELATION_DATA_TLS_CA},
            SecretNotFoundError("secret not found"),
            id="secret not found",
        ),
        pytest.param(
            {1: PROVIDER_RELATION_DATA_TLS_CA, 2: PROVIDER_RELATION_DATA_TLS_CA},
            None,
            id="multiple relations",
        ),
    ],
)
def test_ensure_ready_wraps_invalid_relation_data(relation_databags, error):
    """
    arrange: given OpenSearchRelation whose relation data can't be used.
    act: when ensure_ready is called.
    assert: RelationDataError preserves the original message, relation name and cause.
    """
    relation = _make_relation(requirer=_make_requirer(relation_databags, error=error))

    with pytest.raises(RelationDataError) as exc:
        relation.ensure_ready()

    assert type(exc.value) is RelationDataError
    assert exc.value.relation == OPENSEARCH_RELATION_NAME
    assert isinstance(exc.value.__cause__, RelationDataError)
    assert str(exc.value) == str(exc.value.__cause__)


def test_gen_environment_when_not_configured():
    """
    arrange: given OpenSearchRelation without a _requirer.
    act: when gen_environment is called.
    assert: an empty dictionary is returned.
    """
    relation = _make_relation()

    assert relation.gen_environment() == {}


@pytest.mark.parametrize("relation_data, expected_env", READY_RELATION_DATA_AND_ENV)
def test_gen_environment_when_ready(relation_data, expected_env):
    """
    arrange: given OpenSearchRelation with a valid databag.
    act: when gen_environment is called.
    assert: the OPENSEARCH_* variables of the shared fields are returned.
    """
    relation = _make_relation(requirer=_make_requirer({RELATION_ID: relation_data}))

    assert relation.gen_environment() == expected_env


@pytest.mark.parametrize("relation_databags", NOT_READY_RELATION_DATABAGS)
def test_gen_environment_when_not_ready(relation_databags):
    """
    arrange: given OpenSearchRelation with a databag missing a required field.
    act: when gen_environment is called.
    assert: an empty dictionary is returned and no exception is raised.
    """
    relation = _make_relation(requirer=_make_requirer(relation_databags))

    assert relation.gen_environment() == {}


@pytest.mark.parametrize("relation_data, expected_env", READY_RELATION_DATA_AND_ENV)
def test_generate_opensearch_env(relation_data, expected_env):
    """
    arrange: given a PaaSOpenSearchRelationData built from a valid databag.
    act: when _generate_opensearch_env is called.
    assert: a dictionary with proper keys and identical values is returned.
    """
    relation_data_model = PaaSOpenSearchRelationData.model_validate(relation_data)

    assert OpenSearchRelation._generate_opensearch_env(relation_data_model) == expected_env


def test_generate_opensearch_env_no_relation_data():
    """
    arrange: given no relation data.
    act: when _generate_opensearch_env is called.
    assert: an empty dictionary is returned.
    """
    assert OpenSearchRelation._generate_opensearch_env(None) == {}
