# OMP Voice for Omarchy

A small floating **Herdr terminal running Oh My Pi's live voice mode**, summoned
with `Super + Alt + V`. Click outside the window to dismiss it and end live voice.
The dedicated Herdr session preserves your conversation when the window closes.

This is an independent community plugin, not an official Omarchy or OpenAI plugin.
It does not add voice to Pi or Ask, and it does not replace the Ask plugin.

## Requirements

- Omarchy with shell plugins and **Lua Hyprland configuration** (`hyprland.lua`).
  Tested on Omarchy 4.0.3 / Hyprland 0.56.2; older `.conf` configurations are not supported.
- [Herdr](https://github.com/omacom/herdr) with its agent automation API (tested: 0.9.3).
- [Oh My Pi](https://github.com/can1357/oh-my-pi) with `/live` (tested: 18.8.7).
- Python 3, a configured default terminal (`omarchy-launch-tui`), a microphone,
  and an active Hyprland graphical session.
- OMP authenticated with its `openai-codex` ChatGPT OAuth provider. Open `omp`,
  use `/login` to connect your account, and verify `/live` works before installing.

Install Herdr and OMP following their linked upstream instructions. The setup
checks their presence on PATH but **does not install or update dependencies**.
Codex CLI is not required. Account access, usage limits, and voice availability
are controlled by the provider; leaving voice idle is not guaranteed to be free.

## Install

Run in a terminal on the target Omarchy PC:

```bash
omarchy plugin add https://github.com/Migleve/omarchy-omp-voice.git --enable --yes
python3 "$HOME/.config/omarchy/plugins/migleve.omp-voice/scripts/setup.py"
```

Both steps are necessary: Omarchy's plugin manager deliberately never executes
install hooks. The explicit setup adds the desktop shortcut/window rules.

Then press **Super + Alt + V** to open or close the floating terminal.
On another PC, run the same two commands and log in to OMP there separately.
No credentials or chat history are stored in this repository or copied between PCs.

To change the shortcut, rerun setup:

```bash
python3 "$HOME/.config/omarchy/plugins/migleve.omp-voice/scripts/setup.py" --shortcut 'SUPER + ALT + O'
```

Setup refuses to overwrite another application's shortcut. It adds only a marked
block to `hyprland.lua`, backs up that file, and preserves existing Herdr voice
settings. Generated files live **outside** the plugin checkout so updates stay clean.

## Use

- Shortcut: open/close the terminal; launching activates OMP's default `Ctrl+L` live toggle.
- Click outside: closes on left/right/middle button release, without swallowing
  the click on the underlying app. Moving the pointer alone does not close it.
- Click inside: keep speaking. OMP's space key mutes/unmutes in live mode.
- Esc: exit live mode in OMP; the terminal can remain open.
- Closing the terminal sends Esc to OMP, ending the microphone/voice connection
  while keeping the isolated Herdr session and transcript.
- Shell IPC: `omarchy-shell shell summon migleve.omp-voice '{}'` or
  `omarchy-shell shell hide migleve.omp-voice`.
- CLI: `~/.local/bin/omp-voice --toggle`, `--open`, `--close`, or `--status`.

The existing main Herdr session and its windows are never selected or stopped.
The voice session is named `omp-voice`; do not reuse that session for unrelated
agents. If you customized OMP's live keybinding, restore `Ctrl+L` or adjust
`scripts/voice.py` before using this plugin.

## Update and remove

```bash
omarchy plugin update migleve.omp-voice --yes
python3 "$HOME/.config/omarchy/plugins/migleve.omp-voice/scripts/setup.py"
```

Use the same `--shortcut` if you customized it. To remove, close voice first:

```bash
~/.local/bin/omp-voice --close
python3 "$HOME/.config/omarchy/plugins/migleve.omp-voice/scripts/setup.py" --uninstall
omarchy plugin remove migleve.omp-voice --yes
```

Uninstall removes only the marked configuration block; it intentionally leaves
the inactive generated helper/config, backups, Herdr session and conversations
for recovery. The helper is not usable after removing its plugin source.

## Troubleshooting and privacy

- `hyprctl configerrors` should be empty after setup. Backups are in
  `${XDG_STATE_HOME:-~/.local/state}/omp-voice/backups/`.
- Open `omp` directly and verify `/live` and your audio devices/account first.
- Server logs: `${XDG_STATE_HOME:-~/.local/state}/omp-voice/server.log`.
- `herdr --session omp-voice agent list` inspects only the dedicated voice agent.
- Theme and compact terminal UI: `${XDG_CONFIG_HOME:-~/.config}/herdr/omp-voice.toml`.
  Window geometry: generated `hypr/omp-voice-plugin.lua` (rerunning setup resets it).
- Normal window closure is tested to stop voice. A forcibly killed helper, lost
  compositor, or failed Herdr IPC is not a privacy guarantee: check the system
  microphone indicator and stop `/live` directly in OMP if necessary.
- OMP sends microphone audio to its voice provider while live is active. Review
  upstream privacy and account terms. Plugins run as your user, without a sandbox.

## Development

```bash
python3 -m unittest discover -s tests -v
omarchy plugin validate .
```

Tests cover home/XDG portability, paths with spaces/apostrophes, preservation and
idempotency of configuration, shortcut collision detection, outside-click geometry,
and cleanup when terminal attachment fails. Live integration must also be tested
on a real authenticated Omarchy desktop; CI cannot exercise microphone/provider access.

MIT license. Contributions welcome.

## Español

Instala primero Herdr y OMP, y comprueba que `/live` funciona con tu cuenta.
Ejecuta los dos comandos de **Install** en cada PC. `Super + Alt + V` abre/cierra
la caja flotante; clicar fuera la cierra y termina la voz, conservando la conversación.
No necesitas Codex CLI y no se sincronizan claves ni conversaciones entre equipos.
