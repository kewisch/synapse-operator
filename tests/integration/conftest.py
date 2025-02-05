# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for Synapse charm integration tests."""


import json
import typing
from secrets import token_hex

import pytest
import pytest_asyncio
import requests
from juju.action import Action
from juju.application import Application
from juju.model import Model
from ops.model import ActiveStatus
from pytest import Config
from pytest_operator.plugin import OpsTest

from tests.conftest import SYNAPSE_IMAGE_PARAM, SYNAPSE_NGINX_IMAGE_PARAM

# caused by pytest fixtures, mark does not work in fixtures
# pylint: disable=too-many-arguments, unused-argument

# mypy has trouble to inferred types for variables that are initialized in subclasses.
ACTIVE_STATUS_NAME = typing.cast(str, ActiveStatus.name)  # type: ignore


@pytest_asyncio.fixture(scope="module", name="server_name")
async def server_name_fixture() -> str:
    """Return a server_name."""
    return "my.synapse.local"


@pytest_asyncio.fixture(scope="module", name="another_server_name")
async def another_server_name_fixture() -> str:
    """Return a server_name."""
    return "another.synapse.local"


@pytest_asyncio.fixture(scope="module", name="model")
async def model_fixture(ops_test: OpsTest) -> Model:
    """Return the current testing juju model."""
    assert ops_test.model
    return ops_test.model


@pytest_asyncio.fixture(scope="module", name="model_name")
async def model_name_fixture(ops_test: OpsTest) -> str:
    """Return the current testing juju model name."""
    assert ops_test.model_name
    return ops_test.model_name


@pytest_asyncio.fixture(scope="module", name="synapse_charm")
async def synapse_charm_fixture(pytestconfig: Config):
    """Get value from parameter charm-file."""
    charm = pytestconfig.getoption("--charm-file")
    assert charm, "--charm-file must be set"
    return charm


@pytest_asyncio.fixture(scope="module", name="synapse_image")
def synapse_image_fixture(pytestconfig: Config):
    """Get value from parameter synapse-image."""
    synapse_image = pytestconfig.getoption(SYNAPSE_IMAGE_PARAM)
    assert synapse_image, f"{SYNAPSE_IMAGE_PARAM} must be set"
    return synapse_image


@pytest_asyncio.fixture(scope="module", name="synapse_nginx_image")
def synapse_nginx_image_fixture(pytestconfig: Config):
    """Get value from parameter synapse-nginx-image."""
    synapse_nginx_image = pytestconfig.getoption(SYNAPSE_NGINX_IMAGE_PARAM)
    assert synapse_nginx_image, f"{SYNAPSE_NGINX_IMAGE_PARAM} must be set"
    return synapse_nginx_image


@pytest_asyncio.fixture(scope="module", name="synapse_app_name")
def synapse_app_name_fixture() -> str:
    """Get Synapse application name."""
    return "synapse"


@pytest_asyncio.fixture(scope="module", name="synapse_app_refresh_name")
def synapse_app_refresh_name_fixture() -> str:
    """Get Synapse application name for refresh fixture."""
    return "synapse-refresh"


@pytest_asyncio.fixture(scope="module", name="synapse_app")
async def synapse_app_fixture(
    ops_test: OpsTest,
    synapse_app_name: str,
    synapse_app_refresh_name: str,
    synapse_image: str,
    synapse_nginx_image: str,
    model: Model,
    server_name: str,
    synapse_charm: str,
    postgresql_app: Application,
    postgresql_app_name: str,
    pytestconfig: Config,
):
    """Build and deploy the Synapse charm."""
    use_existing = pytestconfig.getoption("--use-existing", default=False)
    if use_existing:
        return model.applications[synapse_app_name]
    if synapse_app_refresh_name in model.applications:
        await model.remove_application(synapse_app_refresh_name, block_until_done=True)
        await model.wait_for_idle(status=ACTIVE_STATUS_NAME, idle_period=5)
    resources = {
        "synapse-image": synapse_image,
        "synapse-nginx-image": synapse_nginx_image,
    }
    app = await model.deploy(
        f"./{synapse_charm}",
        resources=resources,
        application_name=synapse_app_name,
        series="jammy",
        config={"server_name": server_name},
    )
    async with ops_test.fast_forward():
        await model.wait_for_idle(raise_on_blocked=True, status=ACTIVE_STATUS_NAME)
        await model.relate(f"{synapse_app_name}:database", f"{postgresql_app_name}")
        await model.wait_for_idle(status=ACTIVE_STATUS_NAME)
    return app


@pytest_asyncio.fixture(scope="module", name="synapse_refresh_app")
async def synapse_refresh_app_fixture(
    ops_test: OpsTest,
    model: Model,
    server_name: str,
    synapse_app_refresh_name: str,
    postgresql_app: Application,
    postgresql_app_name: str,
    synapse_charm: str,
):
    """Remove existing Synapse and deploy synapse from Charmhub so the refresh can be tested."""
    async with ops_test.fast_forward():
        synapse_app = await model.deploy(
            "synapse",
            application_name=synapse_app_refresh_name,
            trust=True,
            channel="latest/edge",
            series="jammy",
            config={"server_name": server_name},
        )
        await model.wait_for_idle(
            apps=[synapse_app_refresh_name, postgresql_app_name],
            status=ACTIVE_STATUS_NAME,
            idle_period=5,
        )
        await model.relate(f"{synapse_app_refresh_name}:database", f"{postgresql_app_name}")
        await model.wait_for_idle(idle_period=5)
        await synapse_app.set_config({"enable_mjolnir": "true"})
        await model.wait_for_idle(apps=[synapse_app_refresh_name], idle_period=5, status="blocked")
        app = model.applications[synapse_app_refresh_name]
        await app.refresh(path=f"./{synapse_charm}")
        await model.wait_for_idle(apps=[synapse_app_refresh_name], idle_period=5, status="blocked")
    return app


@pytest_asyncio.fixture(scope="module", name="get_unit_ips")
async def get_unit_ips_fixture(ops_test: OpsTest):
    """Return an async function to retrieve unit ip addresses of a certain application."""

    async def get_unit_ips(application_name: str):
        """Retrieve unit ip addresses of a certain application.

        Args:
            application_name: application name.

        Returns:
            a list containing unit ip addresses.
        """
        _, status, _ = await ops_test.juju("status", "--format", "json")
        status = json.loads(status)
        units = status["applications"][application_name]["units"]
        return tuple(
            unit_status["address"]
            for _, unit_status in sorted(units.items(), key=lambda kv: int(kv[0].split("/")[-1]))
        )

    return get_unit_ips


@pytest.fixture(scope="module", name="external_hostname")
def external_hostname_fixture() -> str:
    """Return the external hostname for ingress-related tests."""
    return "juju.test"


@pytest.fixture(scope="module", name="nginx_integrator_app_name")
def nginx_integrator_app_name_fixture() -> str:
    """Return the name of the nginx integrator application deployed for tests."""
    return "nginx-ingress-integrator"


@pytest_asyncio.fixture(scope="module", name="nginx_integrator_app")
async def nginx_integrator_app_fixture(
    ops_test: OpsTest,
    model: Model,
    synapse_app,
    nginx_integrator_app_name: str,
):
    """Deploy nginx-ingress-integrator."""
    async with ops_test.fast_forward():
        app = await model.deploy(
            "nginx-ingress-integrator",
            application_name=nginx_integrator_app_name,
            trust=True,
            channel="latest/edge",
        )
        await model.wait_for_idle(raise_on_blocked=True, status=ACTIVE_STATUS_NAME)
    return app


@pytest_asyncio.fixture(scope="function", name="another_synapse_app")
async def another_synapse_app_fixture(
    model: Model, synapse_app: Application, server_name: str, another_server_name: str
):
    """Change server_name."""
    # First we guarantee that the first server_name is set
    # Then change it.
    await synapse_app.set_config({"server_name": server_name})

    await model.wait_for_idle()

    await synapse_app.set_config({"server_name": another_server_name})

    await model.wait_for_idle()

    yield synapse_app


@pytest.fixture(scope="module", name="postgresql_app_name")
def postgresql_app_name_app_name_fixture() -> str:
    """Return the name of the postgresql application deployed for tests."""
    return "postgresql-k8s"


@pytest_asyncio.fixture(scope="module", name="postgresql_app")
async def postgresql_app_fixture(
    ops_test: OpsTest, model: Model, postgresql_app_name: str, pytestconfig: Config
):
    """Deploy postgresql."""
    use_existing = pytestconfig.getoption("--use-existing", default=False)
    if use_existing:
        return model.applications[postgresql_app_name]
    async with ops_test.fast_forward():
        await model.deploy(postgresql_app_name, channel="14/stable", trust=True)
        await model.wait_for_idle(status=ACTIVE_STATUS_NAME)


@pytest.fixture(scope="module", name="grafana_app_name")
def grafana_app_name_fixture() -> str:
    """Return the name of the grafana application deployed for tests."""
    return "grafana-k8s"


@pytest_asyncio.fixture(scope="module", name="grafana_app")
async def grafana_app_fixture(
    ops_test: OpsTest,
    model: Model,
    grafana_app_name: str,
):
    """Deploy grafana."""
    async with ops_test.fast_forward():
        app = await model.deploy(
            "grafana-k8s",
            application_name=grafana_app_name,
            channel="stable",
            trust=True,
        )
        await model.wait_for_idle(raise_on_blocked=True, status=ACTIVE_STATUS_NAME)

    return app


@pytest.fixture(scope="module", name="prometheus_app_name")
def prometheus_app_name_fixture() -> str:
    """Return the name of the prometheus application deployed for tests."""
    return "prometheus-k8s"


@pytest_asyncio.fixture(scope="module", name="prometheus_app")
async def deploy_prometheus_fixture(
    ops_test: OpsTest,
    model: Model,
    prometheus_app_name: str,
):
    """Deploy prometheus."""
    async with ops_test.fast_forward():
        app = await model.deploy(
            "prometheus-k8s",
            application_name=prometheus_app_name,
            channel="stable",
            trust=True,
        )
        await model.wait_for_idle(raise_on_blocked=True, status=ACTIVE_STATUS_NAME)

    return app


@pytest.fixture(scope="module", name="user_username")
def user_username_fixture() -> typing.Generator[str, None, None]:
    """Return the a username to be created for tests."""
    yield token_hex(16)


@pytest_asyncio.fixture(scope="module", name="user_password")
async def user_password_fixture(
    synapse_app: Application, user_username: str
) -> typing.AsyncGenerator[str, None]:
    """Return the a username to be created for tests."""
    action_register_user: Action = await synapse_app.units[0].run_action(  # type: ignore
        "register-user", username=user_username, admin=True
    )
    await action_register_user.wait()
    assert action_register_user.status == "completed"
    assert action_register_user.results["register-user"]
    password = action_register_user.results["user-password"]
    assert password
    yield password


@pytest_asyncio.fixture(scope="module", name="access_token")
async def access_token_fixture(
    user_username: str,
    user_password: str,
    synapse_app: Application,
    get_unit_ips: typing.Callable[[str], typing.Awaitable[tuple[str, ...]]],
) -> typing.AsyncGenerator[str, None]:
    """Return the access token after login with the username and password."""
    synapse_ip = (await get_unit_ips(synapse_app.name))[0]
    # login
    sess = requests.session()
    res = sess.post(
        f"http://{synapse_ip}:8080/_matrix/client/r0/login",
        json={
            "identifier": {"type": "m.id.user", "user": user_username},
            "password": user_password,
            "type": "m.login.password",
        },
        timeout=5,
    )
    res.raise_for_status()
    access_token = res.json()["access_token"]
    assert access_token
    yield access_token
