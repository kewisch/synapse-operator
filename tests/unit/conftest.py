# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""pytest fixtures for the unit test."""

# pylint: disable=too-few-public-methods, protected-access

import typing
import unittest.mock

import ops
import pytest
import yaml
from ops.pebble import ExecError
from ops.testing import Harness

import synapse
from charm import SynapseCharm

TEST_SERVER_NAME = "server-name-configured.synapse.com"
TEST_SERVER_NAME_CHANGED = "pebble-layer-1.synapse.com"


def inject_register_command_handler(monkeypatch: pytest.MonkeyPatch, harness: Harness):
    """A helper function for injecting an implementation of the register_command_handler method.

    Args:
        monkeypatch: monkey patch instance.
        harness: harness instance.
    """
    handler_table: dict[str, typing.Callable[[list[str]], tuple[int, str, str]]] = {}

    class ExecProcessStub:
        """A mock object that simulates the execution of a process in the container."""

        def __init__(self, command: list[str], exit_code: int, stdout: str, stderr: str):
            """Initialize the ExecProcessStub object.

            Args:
                command: command to execute.
                exit_code: exit code to return.
                stdout: message to stdout.
                stderr: message to stderr.
            """
            self._command = command
            self._exit_code = exit_code
            self._stdout = stdout
            self._stderr = stderr

        def wait_output(self):
            """Simulate the wait_output method of the container object.

            Returns:
                stdout and stderr from command execution.

            Raises:
                ExecError: something wrong with the command execution.
            """
            if self._exit_code == 0:
                return self._stdout, self._stderr
            raise ExecError(
                command=self._command,
                exit_code=self._exit_code,
                stdout=self._stdout,
                stderr=self._stderr,
            )

    def exec_stub(command: list[str], **_kwargs):
        """A mock implementation of the `exec` method of the container object.

        Args:
            command: command to execute.
            _kwargs: optional arguments.

        Returns:
            ExecProcessStub instance.
        """
        executable = command[0]
        handler = handler_table[executable]
        exit_code, stdout, stderr = handler(command)
        return ExecProcessStub(command=command, exit_code=exit_code, stdout=stdout, stderr=stderr)

    def register_command_handler(
        container: ops.Container | str,
        executable: str,
        handler=typing.Callable[[list[str]], typing.Tuple[int, str, str]],
    ):
        """Registers a handler for a specific executable command.

        Args:
            container: container to register the command.
            executable: executable name.
            handler: handler function to be used.
        """
        container = (
            harness.model.unit.get_container(container)
            if isinstance(container, str)
            else container
        )
        handler_table[executable] = handler
        monkeypatch.setattr(container, "exec", exec_stub)

    monkeypatch.setattr(
        harness, "register_command_handler", register_command_handler, raising=False
    )


@pytest.fixture(name="harness")
def harness_fixture(request, monkeypatch) -> typing.Generator[Harness, None, None]:
    """Ops testing framework harness fixture."""
    monkeypatch.setattr(synapse, "get_version", lambda *_args, **_kwargs: "")
    harness = Harness(SynapseCharm)
    harness.update_config({"server_name": TEST_SERVER_NAME})
    harness.set_model_name("testmodel")  # needed for testing Traefik
    synapse_container: ops.Container = harness.model.unit.get_container(
        synapse.SYNAPSE_CONTAINER_NAME
    )
    harness.set_can_connect(synapse.SYNAPSE_CONTAINER_NAME, True)
    harness.set_can_connect(
        harness.model.unit.containers[synapse.SYNAPSE_NGINX_CONTAINER_NAME], True
    )
    synapse_container.make_dir("/data", make_parents=True)
    # unused-variable disabled to pass constants values to inner function
    command_path = synapse.SYNAPSE_COMMAND_PATH  # pylint: disable=unused-variable
    command_migrate_config = synapse.COMMAND_MIGRATE_CONFIG  # pylint: disable=unused-variable
    exit_code = 0
    if hasattr(request, "param"):
        exit_code = request.param

    def start_cmd_handler(argv: list[str]) -> synapse.ExecResult:
        """Handle the python command execution inside the Synapse container.

        Args:
            argv: arguments list.

        Returns:
            ExecResult instance.

        Raises:
            RuntimeError: command unknown.
        """
        nonlocal command_path, command_migrate_config, exit_code, synapse_container
        match argv:
            case [command_path, command_migrate_config]:  # pylint: disable=unused-variable
                config_content = {
                    "listeners": [
                        {"type": "http", "port": 8080, "bind_addresses": ["::"]},
                    ],
                    "server_name": TEST_SERVER_NAME,
                }
                synapse_container.push(
                    synapse.SYNAPSE_CONFIG_PATH, yaml.safe_dump(config_content), make_dirs=True
                )
                return synapse.ExecResult(exit_code, "", "")
            case _:
                raise RuntimeError(f"unknown command: {argv}")

    inject_register_command_handler(monkeypatch, harness)
    harness.register_command_handler(  # type: ignore # pylint: disable=no-member
        container=synapse_container, executable=command_path, handler=start_cmd_handler
    )
    yield harness
    harness.cleanup()


@pytest.fixture(name="saml_configured")
def saml_configured_fixture(harness: Harness) -> Harness:
    """Harness fixture with saml relation configured"""
    harness.update_config({"server_name": TEST_SERVER_NAME, "public_baseurl": TEST_SERVER_NAME})
    saml_relation_data = {
        "entity_id": "https://login.staging.ubuntu.com",
        "metadata_url": "https://login.staging.ubuntu.com/saml/metadata",
    }
    harness.add_relation("saml", "saml-integrator", app_data=saml_relation_data)
    harness.set_can_connect(synapse.SYNAPSE_CONTAINER_NAME, True)
    harness.set_leader(True)
    return harness


@pytest.fixture(name="container_mocked")
def container_mocked_fixture(monkeypatch: pytest.MonkeyPatch) -> unittest.mock.MagicMock:
    """Mock container base to others fixtures."""
    container = unittest.mock.MagicMock()
    monkeypatch.setattr(container, "can_connect", lambda: True)
    exec_process = unittest.mock.MagicMock()
    exec_process.wait_output = unittest.mock.MagicMock(return_value=(0, 0))
    exec_mock = unittest.mock.MagicMock(return_value=exec_process)
    monkeypatch.setattr(container, "exec", exec_mock)
    return container


@pytest.fixture(name="container_with_path_error_blocked")
def container_with_path_error_blocked_fixture(
    container_mocked: unittest.mock.MagicMock, monkeypatch: pytest.MonkeyPatch
) -> unittest.mock.MagicMock:
    """Mock container that gives an error on remove_path that blocks the action."""
    path_error = ops.pebble.PathError(kind="fake", message="Error erasing directory")
    remove_path_mock = unittest.mock.MagicMock(side_effect=path_error)
    monkeypatch.setattr(container_mocked, "remove_path", remove_path_mock)
    return container_mocked


@pytest.fixture(name="container_with_path_error_pass")
def container_with_path_error_pass_fixture(
    container_mocked: unittest.mock.MagicMock, monkeypatch: pytest.MonkeyPatch
) -> unittest.mock.MagicMock:
    """Mock container that gives an error on remove_path that doesn't block the action."""
    path_error = ops.pebble.PathError(
        kind="generic-file-error", message="unlinkat //data: device or resource busy"
    )
    remove_path_mock = unittest.mock.MagicMock(side_effect=path_error)
    monkeypatch.setattr(container_mocked, "remove_path", remove_path_mock)
    return container_mocked
