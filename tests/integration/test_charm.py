#!/usr/bin/env python3
# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for Synapse charm."""
import json
import logging
import re
import typing

import pytest
import requests
from juju.action import Action
from juju.application import Application
from juju.model import Model
from ops.model import ActiveStatus
from pytest_operator.plugin import OpsTest
from saml_test_helper import SamlK8sTestHelper

import synapse

# caused by pytest fixtures
# pylint: disable=too-many-arguments

# mypy has trouble to inferred types for variables that are initialized in subclasses.
ACTIVE_STATUS_NAME = typing.cast(str, ActiveStatus.name)  # type: ignore

logger = logging.getLogger(__name__)


@pytest.mark.skip(reason="error Waiting for pebble will be addressed in a followup PR")
async def test_synapse_from_refresh_is_up(
    synapse_refresh_app: Application,
    get_unit_ips: typing.Callable[[str], typing.Awaitable[tuple[str, ...]]],
):
    """
    arrange: build and deploy the Synapse charm.
    act: send a request to the Synapse application managed by the Synapse charm.
    assert: the Synapse application should return a correct response.
    """
    for unit_ip in await get_unit_ips(synapse_refresh_app.name):
        response = requests.get(
            f"http://{unit_ip}:{synapse.SYNAPSE_NGINX_PORT}/_matrix/static/", timeout=5
        )
        assert response.status_code == 200
        assert "Welcome to the Matrix" in response.text


async def test_synapse_is_up(
    synapse_app: Application,
    get_unit_ips: typing.Callable[[str], typing.Awaitable[tuple[str, ...]]],
):
    """
    arrange: build and deploy the Synapse charm.
    act: send a request to the Synapse application managed by the Synapse charm.
    assert: the Synapse application should return a correct response.
    """
    for unit_ip in await get_unit_ips(synapse_app.name):
        response = requests.get(
            f"http://{unit_ip}:{synapse.SYNAPSE_NGINX_PORT}/_matrix/static/", timeout=5
        )
        assert response.status_code == 200
        assert "Welcome to the Matrix" in response.text


@pytest.mark.cos
@pytest.mark.usefixtures("synapse_app", "prometheus_app")
async def test_prometheus_integration(
    model: Model,
    prometheus_app_name: str,
    synapse_app_name: str,
    get_unit_ips: typing.Callable[[str], typing.Awaitable[tuple[str, ...]]],
):
    """
    arrange: after Synapse charm has been deployed.
    act: establish relations established with prometheus charm.
    assert: prometheus metrics endpoint for prometheus is active and prometheus has active scrape
        targets.
    """
    await model.add_relation(prometheus_app_name, synapse_app_name)
    await model.wait_for_idle(
        idle_period=30, apps=[synapse_app_name, prometheus_app_name], status=ACTIVE_STATUS_NAME
    )

    for unit_ip in await get_unit_ips(prometheus_app_name):
        query_targets = requests.get(f"http://{unit_ip}:9090/api/v1/targets", timeout=10).json()
        assert len(query_targets["data"]["activeTargets"])


@pytest.mark.cos
@pytest.mark.usefixtures("synapse_app", "prometheus_app", "grafana_app")
async def test_grafana_integration(
    model: Model,
    synapse_app_name: str,
    prometheus_app_name: str,
    grafana_app_name: str,
    get_unit_ips: typing.Callable[[str], typing.Awaitable[tuple[str, ...]]],
):
    """
    arrange: after Synapse charm has been deployed.
    act: establish relations established with grafana charm.
    assert: grafana Synapse dashboard can be found.
    """
    await model.relate(
        f"{prometheus_app_name}:grafana-source", f"{grafana_app_name}:grafana-source"
    )
    await model.relate(synapse_app_name, grafana_app_name)

    await model.wait_for_idle(
        apps=[synapse_app_name, prometheus_app_name, grafana_app_name],
        status=ACTIVE_STATUS_NAME,
        idle_period=60,
    )

    action = await model.applications[grafana_app_name].units[0].run_action("get-admin-password")
    await action.wait()
    password = action.results["admin-password"]
    grafana_ip = (await get_unit_ips(grafana_app_name))[0]
    sess = requests.session()
    sess.post(
        f"http://{grafana_ip}:3000/login",
        json={
            "user": "admin",
            "password": password,
        },
    ).raise_for_status()
    datasources = sess.get(f"http://{grafana_ip}:3000/api/datasources", timeout=10).json()
    datasource_types = set(datasource["type"] for datasource in datasources)
    assert "prometheus" in datasource_types
    dashboards = sess.get(
        f"http://{grafana_ip}:3000/api/search",
        timeout=10,
        params={"query": "Synapse Operator"},
    ).json()
    assert len(dashboards)


@pytest.mark.nginx
@pytest.mark.usefixtures("synapse_app")
async def test_nginx_route_integration(
    model: Model,
    nginx_integrator_app: Application,
    synapse_app_name: str,
    nginx_integrator_app_name: str,
):
    """
    arrange: build and deploy the Synapse charm, and deploy the nginx-integrator.
    act: relate the nginx-integrator charm with the Synapse charm.
    assert: requesting the charm through nginx-integrator should return a correct response.
    """
    await model.add_relation(f"{synapse_app_name}", f"{nginx_integrator_app_name}")
    await nginx_integrator_app.set_config({"service-hostname": synapse_app_name})
    await model.wait_for_idle(idle_period=30, status=ACTIVE_STATUS_NAME)

    response = requests.get(
        "http://127.0.0.1/_matrix/static/", headers={"Host": synapse_app_name}, timeout=5
    )
    assert response.status_code == 200
    assert "Welcome to the Matrix" in response.text


async def test_reset_instance_action(
    model: Model, another_synapse_app: Application, another_server_name: str
):
    """
    arrange: a deployed Synapse charm in a blocked state due to a server_name change.
    act: call the reset_instance action.
    assert: the old instance is deleted and the new one configured.
    """
    unit = model.applications[another_synapse_app.name].units[0]
    # Status string defined in Juju
    # https://github.com/juju/juju/blob/2.9/core/status/status.go#L150
    assert unit.workload_status == "blocked"
    assert "server_name modification is not allowed" in unit.workload_status_message
    action_reset_instance: Action = await another_synapse_app.units[0].run_action(  # type: ignore
        "reset-instance"
    )
    await action_reset_instance.wait()
    assert action_reset_instance.status == "completed"
    assert action_reset_instance.results["reset-instance"]
    assert unit.workload_status == "active"
    config = await model.applications[another_synapse_app.name].get_config()
    current_server_name = config.get("server_name", {}).get("value")
    assert current_server_name == another_server_name


@pytest.mark.asyncio
async def test_workload_version(
    ops_test: OpsTest,
    synapse_app: Application,
    get_unit_ips: typing.Callable[[str], typing.Awaitable[tuple[str, ...]]],
) -> None:
    """
    arrange: a deployed Synapse charm.
    act: get status from Juju.
    assert: the workload version is set and match the one given by Synapse API request.
    """
    await synapse_app.model.wait_for_idle(idle_period=30, apps=[synapse_app.name], status="active")
    _, status, _ = await ops_test.juju("status", "--format", "json")
    status = json.loads(status)
    juju_workload_version = status["applications"][synapse_app.name].get("version", "")
    assert juju_workload_version
    for unit_ip in await get_unit_ips(synapse_app.name):
        res = requests.get(
            f"http://{unit_ip}:{synapse.SYNAPSE_PORT}/_synapse/admin/v1/server_version", timeout=5
        )
        server_version = res.json()["server_version"]
        version_match = re.search(synapse.SYNAPSE_VERSION_REGEX, server_version)
        assert version_match
        assert version_match.group(1) == juju_workload_version


async def test_synapse_enable_mjolnir(
    ops_test: OpsTest,
    synapse_app: Application,
    access_token: str,
    get_unit_ips: typing.Callable[[str], typing.Awaitable[tuple[str, ...]]],
):
    """
    arrange: build and deploy the Synapse charm, create an user, get the access token,
        enable Mjolnir and create the management room.
    act: check Mjolnir health point.
    assert: the Synapse application is active and Mjolnir health point returns a correct response.
    """
    await synapse_app.set_config({"enable_mjolnir": "true"})
    await synapse_app.model.wait_for_idle(
        idle_period=30, timeout=120, apps=[synapse_app.name], status="blocked"
    )
    synapse_ip = (await get_unit_ips(synapse_app.name))[0]
    authorization_token = f"Bearer {access_token}"
    headers = {"Authorization": authorization_token}
    room_body = {
        "creation_content": {"m.federate": False},
        "name": "moderators",
        "preset": "public_chat",
        "room_alias_name": "moderators",
        "room_version": "1",
        "topic": "moderators",
    }
    sess = requests.session()
    res = sess.post(
        f"http://{synapse_ip}:8080/_matrix/client/v3/createRoom",
        json=room_body,
        headers=headers,
        timeout=5,
    )
    res.raise_for_status()
    async with ops_test.fast_forward():
        # using fast_forward otherwise would wait for model config update-status-hook-interval
        await synapse_app.model.wait_for_idle(
            idle_period=30, apps=[synapse_app.name], status="active"
        )

    res = sess.get(f"http://{synapse_ip}:{synapse.MJOLNIR_HEALTH_PORT}/healthz", timeout=5)

    assert res.status_code == 200


@pytest.mark.nginx
@pytest.mark.asyncio
@pytest.mark.usefixtures("nginx_integrator_app")
async def test_saml_auth(  # pylint: disable=too-many-locals
    model: Model,
    model_name: str,
    synapse_app: Application,
    get_unit_ips: typing.Callable[[str], typing.Awaitable[tuple[str, ...]]],
):
    """
    arrange: integrate Synapse with SAML and NGINX charms, upload metadata to samltest.id
        and configure public_baseurl.
    act: simulate a user authenticating via SAML.
    assert: The SAML authentication process is executed successfully.
    """
    synapse_config = await synapse_app.get_config()
    server_name = synapse_config["server_name"]["value"]
    assert server_name
    saml_helper = SamlK8sTestHelper.deploy_saml_idp(model_name)

    saml_integrator_app: Application = await model.deploy(
        "saml-integrator",
        channel="latest/edge",
        series="jammy",
        trust=True,
    )
    await model.wait_for_idle()
    saml_helper.prepare_pod(model_name, f"{saml_integrator_app.name}-0")
    saml_helper.prepare_pod(model_name, f"{synapse_app.name}-0")
    await saml_integrator_app.set_config(
        {
            "entity_id": f"https://{saml_helper.SAML_HOST}/metadata",
            "metadata_url": f"https://{saml_helper.SAML_HOST}/metadata",
        }
    )
    await model.wait_for_idle(idle_period=30)
    await model.add_relation(saml_integrator_app.name, synapse_app.name)
    await model.wait_for_idle(
        idle_period=30,
        apps=[synapse_app.name, saml_integrator_app.name],
        status=ACTIVE_STATUS_NAME,
    )

    session = requests.session()
    headers = {"Host": server_name}
    for unit_ip in await get_unit_ips(synapse_app.name):
        response = session.get(
            f"http://{unit_ip}:{synapse.SYNAPSE_NGINX_PORT}/_synapse/client/saml2/metadata.xml",
            timeout=10,
            headers=headers,
        )
        assert response.status_code == 200
        saml_helper.register_service_provider(name=server_name, metadata=response.text)
        saml_page_path = "_matrix/client/r0/login/sso/redirect/saml"
        saml_page_params = "redirectUrl=http%3A%2F%2Flocalhost%2F&org.matrix.msc3824.action=login"
        redirect_response = session.get(
            f"http://{unit_ip}:{synapse.SYNAPSE_NGINX_PORT}/{saml_page_path}?{saml_page_params}",
            verify=False,
            timeout=10,
            headers=headers,
            allow_redirects=False,
        )
        assert redirect_response.status_code == 302
        redirect_url = redirect_response.headers["Location"]
        saml_response = saml_helper.redirect_sso_login(redirect_url)
        assert f"https://{server_name}" in saml_response.url

        url = saml_response.url.replace(
            f"https://{server_name}", f"http://{unit_ip}:{synapse.SYNAPSE_NGINX_PORT}"
        )
        logged_in_page = session.post(url, data=saml_response.data, headers={"Host": server_name})

        assert logged_in_page.status_code == 200
        assert "Continue to your account" in logged_in_page.text


async def test_synapse_enable_smtp(
    synapse_app: Application,
    get_unit_ips: typing.Callable[[str], typing.Awaitable[tuple[str, ...]]],
    access_token: str,
):
    """
    arrange: build and deploy the Synapse charm, create an user, get the access token
        and enable SMTP.
    act:  try to check if a given email address is not already associated.
    assert: the Synapse application is active and the error returned is the one expected.
    """
    await synapse_app.set_config({"smtp_host": "127.0.0.1"})
    await synapse_app.model.wait_for_idle(
        idle_period=30, apps=[synapse_app.name], status=ACTIVE_STATUS_NAME
    )

    synapse_ip = (await get_unit_ips(synapse_app.name))[0]
    authorization_token = f"Bearer {access_token}"
    headers = {"Authorization": authorization_token}
    sample_check = {
        "id_server": "id.matrix.org",
        "client_secret": "this_is_my_secret_string",
        "email": "example@example.com",
        "send_attempt": "1",
    }
    sess = requests.session()
    res = sess.post(
        f"http://{synapse_ip}:8080/_matrix/client/r0/register/email/requestToken",
        json=sample_check,
        headers=headers,
        timeout=5,
    )

    assert res.status_code == 500
    # If the configuration change fails, will return something like:
    # "Email-based registration has been disabled on this server".
    # The expected error confirms that the e-mail is configured but failed since
    # is not a real SMTP server.
    assert "error was encountered when sending the email" in res.text
