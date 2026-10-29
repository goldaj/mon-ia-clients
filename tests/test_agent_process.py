"""No OpenClaw account or VPS needed: subprocess tests use Python itself."""
import asyncio
import sys
import time
import unittest
from unittest.mock import AsyncMock

from mobile.agent_process import (
    AgentDisconnected, AgentOutputLimit, AgentTimeout, run_agent_process,
)


class AgentRunnerTests(unittest.IsolatedAsyncioTestCase):
    async def test_pipe_buffers_are_drained_concurrently(self):
        command = [sys.executable, "-c",
                   "import sys; sys.stdout.buffer.write(b'a'*300000); "
                   "sys.stderr.buffer.write(b'b'*300000)"]
        code, stdout, stderr = await asyncio.wait_for(
            run_agent_process(command, AsyncMock(return_value=False)), 5)
        self.assertEqual(code, 0)
        self.assertEqual(len(stdout), 300000)
        self.assertEqual(len(stderr), 300000)

    async def test_command_exit_code_preserved(self):
        code, out, err = await run_agent_process(
            [sys.executable, "-c", "import sys;sys.exit(9)"],
            AsyncMock(return_value=False), timeout=3)
        self.assertEqual((code, out, err), (9, b"", b""))

    async def test_output_limit_kills_child(self):
        command = [sys.executable, "-c",
                   "import sys;sys.stdout.buffer.write(b'a'*1000000);sys.stdout.flush()"]
        with self.assertRaises(AgentOutputLimit):
            await asyncio.wait_for(run_agent_process(
                command, AsyncMock(return_value=False),
                max_output=4096), timeout=5)

    async def test_disconnect_terminates_child(self):
        command = [sys.executable, "-c", "import time;time.sleep(60)"]
        with self.assertRaises(AgentDisconnected):
            await asyncio.wait_for(
                run_agent_process(command, AsyncMock(return_value=True),
                                  timeout=5), timeout=5)

    async def test_server_timeout_terminates_child(self):
        command = [sys.executable, "-c", "import time;time.sleep(60)"]
        with self.assertRaises(AgentTimeout):
            await asyncio.wait_for(run_agent_process(
                command, AsyncMock(return_value=False),
                timeout=0.2), timeout=5)

    async def test_request_cancellation_reaps_process(self):
        task = asyncio.create_task(run_agent_process(
            [sys.executable, "-c", "import time;time.sleep(60)"],
            AsyncMock(return_value=False), timeout=60))
        await asyncio.sleep(0.15)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await asyncio.wait_for(task, 5)

    async def test_invalid_bounds_refused(self):
        with self.assertRaises(ValueError):
            await run_agent_process([], AsyncMock(return_value=False))
        with self.assertRaises(ValueError):
            await run_agent_process(["python"], AsyncMock(return_value=False), timeout=0)
