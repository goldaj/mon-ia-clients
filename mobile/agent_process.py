"""Bounded, cancellable OpenClaw process runner for the Linux VPS client.

Always drain stdout/stderr concurrently. Waiting for the process before reading
pipes can deadlock when OpenClaw emits more than a pipe buffer.
"""
import asyncio
import os
import signal


class AgentTimeout(Exception):
    pass


class AgentDisconnected(Exception):
    pass


class AgentOutputLimit(Exception):
    pass


async def _read_limited(stream, limit):
    parts = []
    size = 0
    while True:
        part = await stream.read(16384)
        if not part:
            break
        size += len(part)
        if size > limit:
            raise AgentOutputLimit()
        parts.append(part)
    return b"".join(parts)


async def _collect(process, max_output):
    stdout_reader = asyncio.create_task(_read_limited(process.stdout, max_output))
    stderr_reader = asyncio.create_task(_read_limited(process.stderr, max_output))
    try:
        stdout, stderr = await asyncio.gather(stdout_reader, stderr_reader)
        returncode = await process.wait()
        return returncode, stdout, stderr
    finally:
        for reader in (stdout_reader, stderr_reader):
            if not reader.done():
                reader.cancel()
        await asyncio.gather(stdout_reader, stderr_reader, return_exceptions=True)


async def _wait_disconnect(check):
    while True:
        if await check():
            return
        await asyncio.sleep(0.25)


async def _terminate(process):
    # Linux subprocesses have their own session so descendants are stopped too.
    try:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGTERM)
        elif process.returncode is None:
            process.terminate()
    except ProcessLookupError:
        pass
    try:
        await asyncio.wait_for(process.wait(), 3)
    except asyncio.TimeoutError:
        try:
            if os.name == "posix":
                os.killpg(process.pid, signal.SIGKILL)
            elif process.returncode is None:
                process.kill()
        except ProcessLookupError:
            pass
        await process.wait()


async def run_agent_process(command, is_disconnected, *, timeout=930,
                            max_output=2 * 1024 * 1024):
    """Return (exit_code, stdout_bytes, stderr_bytes); no shell is invoked.

    A client disconnect, timeout, cancellation or too much output terminates the
    entire process group and reaps the child. No raw output enters log messages.
    """
    if not command or timeout <= 0 or max_output <= 0:
        raise ValueError("invalid process limits")
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        start_new_session=(os.name == "posix"),
    )
    work = asyncio.create_task(_collect(process, max_output))
    disconnected = asyncio.create_task(_wait_disconnect(is_disconnected))
    completed = False
    try:
        done, _ = await asyncio.wait(
            (work, disconnected), timeout=timeout,
            return_when=asyncio.FIRST_COMPLETED)
        if work in done:
            result = await work
            completed = True
            return result
        if disconnected in done:
            await disconnected
            raise AgentDisconnected()
        raise AgentTimeout()
    finally:
        if not completed:
            await _terminate(process)
        for task in (work, disconnected):
            if not task.done():
                task.cancel()
        await asyncio.gather(work, disconnected, return_exceptions=True)
