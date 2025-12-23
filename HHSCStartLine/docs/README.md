HHSC Start Line

To build the application:

python -m zipapp src -o build/startline-py3-YYYYMMDD-HHmm.zip

and then recreate the symbolic link:

rm startline.zip
ln -s startline-py3-YYYYMMDD-HHmm.zip startline.zip

## Installation

On Linux, you'll need permissions to the tty device for the EasyDaq relay board. You can add your user to the dialout group:

sudo usermod -a -G dialout $USER

