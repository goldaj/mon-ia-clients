import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from pydantic import ValidationError
from mobile import app as mobile_app


class AgentEndpointTests(unittest.IsolatedAsyncioTestCase):
    async def test_agent_returns_text_from_json(self):
        request = SimpleNamespace(is_disconnected=AsyncMock(return_value=False))
        with patch.object(mobile_app, "OPENCLAW", __file__), patch.object(
            mobile_app, "run_agent_process",
            AsyncMock(return_value=(0, b'{"payloads":[{"text":"Hello"}]}', b""))):
            result = await mobile_app.chat_agent(
                mobile_app.AgentRequest(message="salut", session_key="mobile-abc"),
                request)
        self.assertEqual(result["text"], "Hello")

    async def test_subprocess_error_must_not_leak_stderr(self):
        request = SimpleNamespace(is_disconnected=AsyncMock(return_value=False))
        with patch.object(mobile_app, "OPENCLAW", __file__), patch.object(
            mobile_app, "run_agent_process",
            AsyncMock(return_value=(1, b"", b"SECRET TOKEN"))):
            with self.assertRaises(HTTPException) as err:
                await mobile_app.chat_agent(
                    mobile_app.AgentRequest(message="salut", session_key="mobile-abc"),
                    request)
        self.assertEqual(err.exception.status_code, 502)
        self.assertNotIn("SECRET", str(err.exception.detail))

    async def test_input_is_rejected_before_launch(self):
        with self.assertRaises(ValidationError):
            mobile_app.AgentRequest(message="x", session_key="../unsafe")
        with self.assertRaises(ValidationError):
            mobile_app.AgentRequest(message="x" * 8193)
        with self.assertRaises(ValidationError):
            mobile_app.AgentRequest(message="x", session_key="")
