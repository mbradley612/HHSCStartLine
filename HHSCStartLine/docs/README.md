HHSC Start Line

To build the application:

python -m zipapp src -o build/startline-py3-YYYYMMDD-HHmm.zip

and then recreate the symbolic link:

rm build/startline-py3.zip
ln -sf startline-py3-YYYYMMDD-HHmm.zip build/startline-py3.zip

## Dependencies

Python 3 packages (install via apt on Debian/Ubuntu):

- `python3-tk` — Tkinter GUI bindings
- `python3-pyaudio` — audio playback (also requires system headers `portaudio19-dev` and `libasound2-dev`)
- `python3-serial` — serial communication with EasyDaq relay board (optional, only needed if lights are enabled)

System packages required to build PyAudio:

- `portaudio19-dev` — PortAudio C development headers
- `libasound2-dev` — ALSA sound library headers

Install everything on Debian/Ubuntu:

```
sudo apt install python3-tk python3-pyaudio python3-serial portaudio19-dev libasound2-dev
```

## Installation

On Linux, you'll need permissions to the tty device for the EasyDaq relay board. You can add your user to the dialout group:

sudo usermod -a -G dialout $USER

