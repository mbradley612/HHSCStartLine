StartLine Python3

On Ubuntu you need the python3-tk package to get the Tk bindings. Add it to the apt install step:

```
bash
sudo apt update
sudo apt install python3 python3-venv python3-pip python3-tk python3-serial python3-pyaudio\
    build-essential git unzip \
    libsdl2-2.0-0 libsdl2-dev libsdl2-image-2.0-0 libsdl2-image-dev \
    libsdl2-mixer-2.0-0 libsdl2-mixer-dev libsdl2-ttf-2.0-0 libsdl2-ttf-dev \
    portaudio19-dev libasound2-dev \
    libfreetype6-dev libjpeg-dev zlib1g-dev \
    libudev-dev libusb-1.0-0-dev \
    libtool pkg-config \
    libffi-dev
```

After installing, verify Tk is available in your venv:

```
python -c "import tkinter; print(tkinter.TkVersion)"
```
If that prints a version number, _tkinter is good to go.