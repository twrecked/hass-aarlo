"""Config flow: log in during setup and let the user pick a real 2FA factor.

`ArloLogin` is replaced by a scripted fake, so no Arlo network access.
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pyaarlo = pytest.importorskip("pyaarlo")
if not hasattr(pyaarlo, "LoginStep"):
    pytest.skip("pyaarlo has no step by step login yet", allow_module_level=True)
LoginStep = pyaarlo.LoginStep

from custom_components.aarlo import config_flow
from custom_components.aarlo.config_flow import AarloFlowHandler


EMAIL = {"factorId": "fid-email", "factorType": "EMAIL", "factorNickname": "home@example.com"}
PHONE = {"factorId": "fid-push", "factorType": "PUSH", "factorNickname": "Pixel 9"}

USER_INPUT = {
    "username": "user@example.com",
    "password": "synthetic-password",
    "add_aarlo_prefix": True,
}


class FakeLogin:
    """Plays back a script of `LoginStep`s per call."""

    instances: list["FakeLogin"] = []

    def __init__(self, start=LoginStep.NEEDS_FACTOR, choose=LoginStep.AWAITING_PUSH,
                 polls=(LoginStep.SUCCESS,), codes=(LoginStep.SUCCESS,), **options):
        self.options = options
        self.factors = [EMAIL, PHONE]
        self.push_poll = 0
        self.last_error = "synthetic error"
        self._start = start
        self._choose = choose
        self._polls = list(polls)
        self._codes = list(codes)
        self.chosen = []
        self.codes = []
        self.closed = False
        FakeLogin.instances.append(self)

    async def start(self):
        return self._start

    async def choose_factor(self, factor_id):
        self.chosen.append(factor_id)
        return self._choose

    async def poll_push(self):
        return self._polls.pop(0)

    async def submit_code(self, code):
        self.codes.append(code)
        return self._codes.pop(0)

    async def close(self):
        self.closed = True


def _flow():
    flow = AarloFlowHandler()
    flow.hass = SimpleNamespace(data={}, async_create_task=asyncio.ensure_future)
    flow.flow_id = "flow-1"
    flow.handler = "aarlo"
    flow.context = {}
    return flow


def _patches(flow, **script):
    FakeLogin.instances = []

    def make(**options):
        return FakeLogin(**script, **options)

    return (
        patch.object(flow, "_async_current_entries", return_value=[]),
        patch.object(flow, "_async_login_options", AsyncMock(return_value={"user_agent": "linux"})),
        patch.object(config_flow, "ArloLogin", make),
    )


async def _finish_push(flow):
    """Drive the progress step the way the frontend does."""
    result = await flow.async_step_await_push()
    while result["type"] == "progress":
        await flow._push_task
        result = await flow.async_step_await_push()
    assert result["type"] == "progress_done"
    return await getattr(flow, f"async_step_{result['step_id']}")()


@pytest.mark.asyncio
async def test_user_form_has_no_tfa_guesswork():
    flow = _flow()
    with patch.object(flow, "_async_current_entries", return_value=[]):
        result = await flow.async_step_user()
    assert result["type"] == "form"
    fields = [str(k) for k in result["data_schema"].schema]
    assert "manual_tfa" in fields
    assert "tfa_type" not in fields


@pytest.mark.asyncio
async def test_push_factor_creates_push_entry():
    flow = _flow()
    p1, p2, p3 = _patches(flow, polls=(LoginStep.AWAITING_PUSH, LoginStep.SUCCESS))
    with p1, p2, p3:
        result = await flow.async_step_user(USER_INPUT)
        assert result["type"] == "form"
        assert result["step_id"] == "choose_factor"

        result = await flow.async_step_choose_factor({"factor_id": "fid-push"})
        assert result["type"] == "progress"
        result = await _finish_push(flow)

    login = FakeLogin.instances[0]
    assert login.options == {"user_agent": "linux"}
    assert login.chosen == ["fid-push"]
    assert login.closed
    assert result["type"] == "create_entry"
    assert result["data"] == {
        "username": "user@example.com",
        "password": "synthetic-password",
        "add_aarlo_prefix": True,
        "tfa_type": "push",
        "tfa_source": "push",
        "tfa": "push",
        "tfa_factor_id": "fid-push",
    }


@pytest.mark.asyncio
async def test_denied_push_goes_back_to_the_choice():
    flow = _flow()
    p1, p2, p3 = _patches(flow, polls=(LoginStep.FAILED,))
    with p1, p2, p3:
        await flow.async_step_user(USER_INPUT)
        await flow.async_step_choose_factor({"factor_id": "fid-push"})
        result = await _finish_push(flow)
    assert result["type"] == "form"
    assert result["step_id"] == "choose_factor"
    assert result["errors"] == {"base": "push_failed"}


@pytest.mark.asyncio
async def test_code_factor_with_a_retry():
    flow = _flow()
    p1, p2, p3 = _patches(flow, choose=LoginStep.AWAITING_CODE,
                          codes=(LoginStep.AWAITING_CODE, LoginStep.SUCCESS))
    with p1, p2, p3:
        await flow.async_step_user(USER_INPUT)
        result = await flow.async_step_choose_factor({"factor_id": "fid-email"})
        assert result["step_id"] == "enter_code"
        assert result["description_placeholders"]["factor"] == "home@example.com (Email)"

        result = await flow.async_step_enter_code({"code": "000000"})
        assert result["type"] == "form"
        assert result["errors"] == {"base": "wrong_code"}

        result = await flow.async_step_enter_code({"code": "123456"})

    assert FakeLogin.instances[0].codes == ["000000", "123456"]
    assert result["type"] == "create_entry"
    assert result["data"]["tfa"] == "email:console"
    assert result["data"]["tfa_source"] == "console"
    assert result["data"]["tfa_factor_id"] == "fid-email"


@pytest.mark.asyncio
async def test_trusted_browser_needs_no_factor():
    flow = _flow()
    p1, p2, p3 = _patches(flow, start=LoginStep.SUCCESS)
    with p1, p2, p3:
        result = await flow.async_step_user(USER_INPUT)
    assert result["type"] == "create_entry"
    assert result["data"]["tfa"] == "none"
    assert "tfa_factor_id" not in result["data"]


@pytest.mark.asyncio
async def test_bad_password_shows_the_form_again():
    flow = _flow()
    p1, p2, p3 = _patches(flow, start=LoginStep.FAILED)
    with p1, p2, p3:
        result = await flow.async_step_user(USER_INPUT)
    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "invalid_auth"}
    assert FakeLogin.instances[0].closed


@pytest.mark.asyncio
async def test_manual_tfa_skips_the_login():
    flow = _flow()
    p1, p2, p3 = _patches(flow)
    with p1, p2, p3:
        result = await flow.async_step_user({**USER_INPUT, "manual_tfa": True})
        assert result["type"] == "form"
        assert result["step_id"] == "manual_tfa"
        result = await flow.async_step_manual_tfa({"tfa_type": "PUSH"})
    assert FakeLogin.instances == []
    assert result["type"] == "create_entry"
    assert result["data"]["username"] == "user@example.com"
    assert result["data"]["tfa"] == "push"


@pytest.mark.asyncio
async def test_reconfigure_drops_the_pinned_factor():
    flow = _flow()
    entry = SimpleNamespace(
        entry_id="e1",
        data={"username": "u@example.com", "password": "pw", "tfa": "push",
              "tfa_factor_id": "fid-push"},
    )
    with (
        patch.object(flow, "_get_entry", return_value=entry),
        patch.object(flow, "async_update_reload_and_abort",
                     return_value={"type": "abort"}) as abort,
    ):
        await flow.async_step_reconfigure({
            "username": "u@example.com", "password": "pw", "tfa_type": "IMAP",
            "tfa_host": "imap.example.com", "tfa_username": "u", "tfa_password": "p",
            "add_aarlo_prefix": True,
        })
    assert "tfa_factor_id" not in abort.call_args[1]["data"]
