"""Explicitly trusted command execution. This is NOT a security sandbox."""
import os
import signal
import subprocess
import tempfile
import time
from pathlib import Path

MAX_LOG = 1_000_000

def run_command(command, cwd, timeout=60, trusted=False):
    if not trusted:
        raise ValueError("Execution requires --allow-exec for trusted code; use an isolated VM for untrusted code")
    if not isinstance(command, list) or not command or not all(isinstance(x, str) for x in command) or not command[0]:
        raise ValueError("Command must be a nonempty JSON list of strings")
    if not 0 < timeout <= 86400:
        raise ValueError("Timeout must be in (0, 86400]")
    # Deliberately do not pass API keys or the full environment to candidate commands.
    env = {k: os.environ[k] for k in ("PATH", "SYSTEMROOT", "LANG") if k in os.environ}
    env.update({"PYTHONIOENCODING": "utf-8", "ORCHESTRATE_EVAL": "1"})
    start = time.monotonic()
    timed_out = False
    truncated = False
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        process = subprocess.Popen(command, cwd=Path(cwd).resolve(), env=env, stdout=out, stderr=err,
                                   stdin=subprocess.DEVNULL, start_new_session=(os.name == "posix"))
        while process.poll() is None:
            if time.monotonic() - start > timeout or os.fstat(out.fileno()).st_size + os.fstat(err.fileno()).st_size > MAX_LOG:
                timed_out = time.monotonic() - start > timeout
                truncated = not timed_out
                if os.name == "posix":
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass  # The process may finish between poll and kill.
                else:
                    process.kill()
                break
            time.sleep(0.02)
        process.wait()
        truncated = truncated or os.fstat(out.fileno()).st_size + os.fstat(err.fileno()).st_size > MAX_LOG
        # Kill remaining children in our process group (not a containment guarantee).
        if os.name == "posix":
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        out.seek(0); err.seek(0)
        stdout = out.read(MAX_LOG).decode("utf-8", errors="replace")
        stderr = err.read(MAX_LOG).decode("utf-8", errors="replace")
    return {"command": command, "exit_code": process.returncode,
            "wall_seconds": round(time.monotonic() - start, 4), "timed_out": timed_out,
            "log_limit_exceeded": truncated, "stdout": stdout, "stderr": stderr,
            "status": "pass" if process.returncode == 0 and not timed_out and not truncated else "fail",
            "resource_limits": "Wall time and sampled log size only; no memory/network/filesystem sandbox",
            "tokens": None, "cost": None, "peak_memory_bytes": None}
