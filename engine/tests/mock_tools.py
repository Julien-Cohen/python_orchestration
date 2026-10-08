import socket
import subprocess
import sys
import time
from pathlib import Path


def start_mock_agent(agent_dir, agent_file, port:int, mock: str | None = None):
    agent_script = (
            Path(__file__).parent
            / agent_dir
            / ("%s" % agent_file)
    )
    command = [sys.executable, str(agent_script), ("--port=%s" % port)]
    if mock is not None:
        command.append(("--mock-string=%s" % mock))
    process = subprocess.Popen(command)

    try:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError("Agent server exited before becoming ready")
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                    break
            except OSError:
                time.sleep(0.1)
        else:
            raise RuntimeError("Agent server did not become ready on port %s" % port)

        yield
    finally:
        process.terminate()
        process.wait(timeout=5)
