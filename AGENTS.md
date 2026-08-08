# AGENTS.md

Python 3 Tkinter app that runs sailing-club start-line sequences for Hill Head SC (horns, countdown beeps, EasyDaq relay lights, race/finish tracking). No build system, no CI, no `requirements.txt`/`pyproject.toml`, no framework.

## Layout

- `HHSCStartLine/` — the actual project. **Do all work here.**
- `HHSCStartLine/src/` — packages: `model/` (domain + `Signal` observer in `utils.py`), `controllers/` (Tk wiring), `screenui/` (Tk UI + audio), `lightsui/` (serial relay), `persistence/` (pickle recovery). Entrypoint `src/__main__.py`.
- `install/` — legacy Linux deployment notes; describes **python2** pip steps (stale, app is py3 now).
- `tools/` — Arduino sketches simulating the EasyDaq relay (`easy_daq_relay_simulator.ino`, `easydaq_usb8pr_sr_sim.ino`).

## Commands

- Run from source: `python3 HHSCStartLine/src/__main__.py HHSCStartLine/startline.ini` (paths in the ini like `media/*.wav` and `data/currentRace.dmp` are relative to cwd, so run from repo root).
- Build (per `docs/README.md`): from `HHSCStartLine/`:
  `python3 -m zipapp src -o build/startline-py3-YYYYMMDD-HHmm.zip`
  then `rm build/startline.zip && ln -s startline-py3-<name>.zip build/startline.zip`
- Run zip: `python3 build/startline.zip startline.ini`. Note the tracked `build/startline.zip` symlink currently points at `startline-py3-20251223-2105.zip`, which is **not in the repo** — the symlink is dangling; rebuild before running.
- Tests: from `HHSCStartLine/`, run `python3 -m unittest discover -s tests` (29 tests: model sequences/recall/persistence, lights countdown incl. the 3-minute prep and flash rules, gun/beep scheduling, audio clip channels/durations). Also `python3 -m unittest model.testboat` from `HHSCStartLine/src` (legacy, still passing). `model.testrace` is broken/outdated — it imports a `Race` class that no longer exists in `race.py` (only `RaceManager`/`Boat`/`Fleet`/`Finish` remain). Don't rely on it; don't "fix" it by inventing a `Race` class.

## Architecture / threading

- Tk main thread is the UI. `AudioManager` (pyaudio), `EasyDaqUSBRelay` (pyserial), and `RaceRecoveryManager` each run in daemon threads started from `__main__.py`.
- Threads never touch Tk. They consume a `queue.Queue` of command objects; controllers schedule Tk work with `tkRoot.after(...)` / `update_idletasks()`. `model/utils.py` `Signal` is the observer pattern for model→controller notifications.
- Persistence: `RaceManager.__getstate__`/`__setstate__` pickle the manager (sans `Signal`) to `data/currentRace.dmp` on every change; on startup the app prompts to recover if that file exists. `data/` and `logs/` are gitignored and created at runtime.
- Lights: `[Lights] enabled=Y` + `comPort` in `startline.ini` (macOS example `/dev/cu.usbmodem2143301`). EasyDaq reconnect loop is iterative (committed change `eb6868a`). Running needs pyaudio + pyserial installed (audio is always imported).

## Hardware / install docs

Authoritative install + hardware details live in the GitHub wiki (https://github.com/mbradley612/HHSCStartLine/wiki/Installation). Repo-local `install/` and the wiki's `Software-Installation` page are **python2-era and stale**; the py3 setup doc is `HHSCStartLine/docs/StartLinePy3.md`.

- Production hardware: Fit-PC running Ubuntu, EasyDaq **USB8PR2 8-channel relay** card (one channel per start-sequence light), a Delcom USB HID button, plus amplifier + outdoor speakers. The Arduino sketches in `tools/` simulate the EasyDaq board.
- The Delcom button is configured to emit **F1**; there is normally no keyboard. The app binds `<F1>` → gun+finish and `<F2>` → gun (`src/controllers/controllers.py:386-392`).
- Audio is split across stereo channels: **left = outdoor speakers** (horns/gun, e.g. `1.5-Second-Horn-left.wav`), **right = indoor speaker** (warning beeps, e.g. `beep-right.wav`). The wav names encode this; don't replace a clip with a mono or opposite-channel file.
- The EasyDaq needs a serial port and Linux dialout/tty group perms (see wiki); the `[Lights] comPort` in `startline.ini` is the only wiring.
- **Simulators**: the Arduino sketches in `tools/` (`easy_daq_relay_simulator/`, `easydaq_usb8pr_sr_sim/`) mimic the EasyDaq's serial protocol — both accept the `B` (set direction) and `C` (write relay states) commands over **9600 8N1**, matching `lightsui/hardware.py`. Flash one to an Arduino, wire LEDs to pins 2–9, plug it in via USB, and point `[Lights] comPort` at its port to exercise the full lights logic without the real relay card.

## Gotchas

- `HHSCStartLine/src/screenui/raceview.py:45` forces ttk theme `clam` because macOS `aqua` ignores `TButton` padding — preserve this when touching button sizing.
- `HHSCStartLine/logging.conf` has a hardcoded absolute log path from an old checkout (`/Users/mbradley/git/HHSCStartLine/...`) — point it at this repo or it silently creates nothing where you expect.
- `.pyc` files are committed despite `.gitignore`; per-dir `.gitignore` files can't untrack them. Don't add more, but don't try to purge them via gitignore.
- `defaultFleetNames` in the ini is a comma-separated list; empty sections crash `config.get`.
- python2 remnants to ignore: `.pydevproject` (says 2.7), `get-pip.py`, `install/README.md`. Python 3 setup lives in `docs/StartLinePy3.md`.
