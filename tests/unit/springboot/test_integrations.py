# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Springboot charm unit tests for integrations."""

# Very similar cases to other frameworks. Disable duplicated checks.
# pylint: disable=R0801

from ops import testing

from examples.springboot.charm.src.charm import SpringBootCharm


def test_smtp_integration(
    base_state,
) -> None:
    """
    arrange: add smtp relation to the base state.
    act: start the springboot charm and set springboot-app container to be ready.
    assert: the springboot charm should have the smtp related env variables.
    """
    base_state["relations"].append(
        testing.Relation(
            endpoint="smtp",
            interface="smtp-integrator",
            remote_app_data={
                "auth_type": "none",
                "domain": "example.com",
                "host": "mailcatcher",
                "port": "1025",
                "skip_ssl_verify": "false",
                "transport_security": "none",
            },
        )
    )
    state = testing.State(**base_state)
    context = testing.Context(
        charm_type=SpringBootCharm,
    )

    out = context.run(context.on.config_changed(), state)
    environment = list(out.containers)[0].plan.services["spring-boot"].environment
    assert out.unit_status == testing.ActiveStatus()

    smtp_relation = out.get_relations("smtp")
    assert len(smtp_relation) == 1

    assert environment["spring.mail.host"] == "mailcatcher"
    assert environment["spring.mail.port"] == 1025
    assert environment["spring.mail.username"] == "None@example.com"
    assert environment["spring.mail.password"] is None
    assert environment["spring.mail.properties.mail.smtp.auth"] == "none"
    assert environment["spring.mail.properties.mail.smtp.starttls.enable"] == "false"
