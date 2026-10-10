#!/usr/bin/python3
"""Toggle a compact floating terminal running OMP live in its own Herdr session."""
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import uuid

SESSION = "omp-voice"
APP_ID = "org.omarchy.omp-voice"
ROOT = Path.home()
STATE = Path(os.environ.get("XDG_STATE_HOME", ROOT / ".local/state")) / "omp-voice"
CONFIG = Path(os.environ.get("XDG_CONFIG_HOME", ROOT / ".config")) / "herdr/omp-voice.toml"
LAUNCHER = Path(__file__).resolve()
ENV = {key: value for key, value in os.environ.items() if not key.startswith("HERDR_")}
ENV["HERDR_CONFIG_PATH"] = str(CONFIG)


def run(argv, *, check=True, timeout=30):
    return subprocess.run(argv, env=ENV, capture_output=True, text=True,
                          check=check, timeout=timeout)


def api(*args, timeout=30):
    response = run(["herdr", "--session", SESSION, *args], timeout=timeout)
    return json.loads(response.stdout)["result"]


def prepare():
    def server_running():
        return run(["herdr", "--session", SESSION, "workspace", "list"], check=False).returncode == 0

    if not server_running():
        with (STATE / "server.log").open("a") as log:
            subprocess.Popen(["herdr", "--session", SESSION, "server"], env=ENV,
                             cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log,
                             stderr=log, start_new_session=True)
        deadline = time.monotonic() + 15
        while not server_running():
            if time.monotonic() >= deadline:
                raise RuntimeError("No se pudo iniciar la sesión de Herdr para voz.")
            time.sleep(0.15)
    agents = api("agent", "list")["agents"]
    matches = [agent for agent in agents if agent.get("name") == "omp-voice"]
    if len(matches) > 1:
        raise RuntimeError("Hay más de un agente de voz; revisa la sesión omp-voice.")
    if matches:
        return matches[0]["pane_id"]
    spaces = api("workspace", "list")["workspaces"]
    panes = []
    for space in spaces:
        panes.extend(api("pane", "list", "--workspace", space["workspace_id"])["panes"])
    if not panes:
        created = api("workspace", "create", "--cwd", str(ROOT), "--label", "Voz OMP", "--no-focus")
        pane_id = created["root_pane"]["pane_id"]
    elif len(panes) == 1:
        pane_id = panes[0]["pane_id"]
    else:
        raise RuntimeError("La sesión de voz tiene varios paneles; no se elegirá uno al azar.")
    api("agent", "start", "omp-voice", "--kind", "omp", "--pane", pane_id,
        "--timeout", "60000", "--", "--no-title", timeout=65)
    return pane_id


def stop_voice(pane_id):
    # Esc ends OMP's live visualizer; the dedicated session retains its transcript.
    try:
        api("agent", "send-keys", pane_id, "esc", timeout=10)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"No se pudo detener la voz: {error}", file=sys.stderr)


def requested(token):
    if token is None:
        return True
    try:
        return (STATE / 'launch-request').read_text() == token
    except FileNotFoundError:
        return False


def client(token=None):
    if not requested(token):
        return
    with (STATE / "client.lock").open("a") as lock:
        deadline = time.monotonic() + 15
        while True:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise RuntimeError("Previous voice window is still closing; try again shortly.")
                time.sleep(0.1)
        child = None
        pane_id = None
        voice_requested = False

        def interrupted(signum, frame):
            raise KeyboardInterrupt

        for signum in (signal.SIGHUP, signal.SIGTERM, signal.SIGINT):
            signal.signal(signum, interrupted)
        try:
            if not requested(token):
                return
            pane_id = prepare()
            api("agent", "wait", pane_id, "--until", "idle", "--until", "done",
                "--timeout", "30000", timeout=35)
            if not requested(token):
                return
            api("agent", "focus", pane_id)
            voice_requested = True
            api("agent", "send-keys", pane_id, "ctrl+l")
            child = subprocess.Popen(["herdr", "--session", SESSION], env=ENV, cwd=ROOT)
            child.wait()
        finally:
            for signum in (signal.SIGHUP, signal.SIGTERM, signal.SIGINT):
                signal.signal(signum, signal.SIG_IGN)
            if pane_id and voice_requested:
                stop_voice(pane_id)
            if child and child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait()
            if token is not None and requested(token):
                (STATE / 'launch-request').unlink(missing_ok=True)


def toggle(action="toggle"):
    with (STATE / "toggle.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        windows = json.loads(run(["hyprctl", "clients", "-j"]).stdout)
        matching = [window for window in windows if window.get("class") == APP_ID]
        request = STATE / 'launch-request'
        pending = request.exists() and time.time() - request.stat().st_mtime < 120
        if action == "close" or (action == "toggle" and (matching or pending)):
            request.unlink(missing_ok=True)
            for window in matching:
                selector = "address:" + window["address"]
                run(["hyprctl", "dispatch",
                     'hl.dsp.window.close({ window = "' + selector + '" })'])
            return
        if matching or pending:
            return
        token = uuid.uuid4().hex
        request.write_text(token)
        subprocess.Popen(["omarchy-launch-tui", "--app-id=" + APP_ID,
                          str(LAUNCHER), "--client", token], env=ENV, cwd=ROOT,
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True)


def main():
    STATE.mkdir(parents=True, exist_ok=True)
    mode = sys.argv[1:] or ["--toggle"]
    if mode == ["--toggle"]:
        toggle()
    elif mode == ["--open"]:
        toggle("open")
    elif mode == ["--close"]:
        toggle("close")
    elif mode == ["--status"]:
        windows = json.loads(run(["hyprctl", "clients", "-j"]).stdout)
        print("open" if any(w.get("class") == APP_ID for w in windows) else "closed")
    elif mode == ["--client"]:
        client()
    elif len(mode) == 2 and mode[0] == "--client":
        client(token=mode[1])
    elif mode == ["--prepare"]:
        print(prepare())
    else:
        raise RuntimeError("Usage: omp-voice [--toggle|--open|--close|--status|--client|--prepare]")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
        detail = getattr(error, "stderr", None) or str(error)
        print(f"OMP Voz: {detail}", file=sys.stderr)
        if sys.stdout.isatty():
            input("Pulsa Intro para cerrar.")
        sys.exit(1)
