## Startline dependencies

Install python dependencies

```
sudo apt install python-tk 
```



On debian

```
sudo apt install python-pyaudio
```



On Ubuntu, make sure you have the python2 pip, see https://linuxize.com/post/how-to-install-pip-on-ubuntu-20.04/. And then

```
sudo apt-get install portaudio19-dev
sudo apt install python2-dev
pip2 install PyAudio
```

On debian

```
sudo apt install python-serial
```

On ubuntu

```
pi2 install pyserial
```





## Install openbox



Autostart



openbox autostart





## Disable screen saver

1. Open up `/etc/lightdm/lightdm.conf` using your favorite text editor (I prefer `nano`).

2. Look for the line

    

   ```
   #xserver-command=X
   ```

   . Change it to

    

   ```
   xserver-command=X -s 0 dpms
   ```

   - It should be at line 87 if things don't change.

3. Save and reboot.

### Permissions for /dev/ttyUSB0

As root

```usermod -a -G tty startline ```

 ```usermod -a -G dialout startline ```



### Configuring the Delcom button

Configuring app for windows

https://www.delcomproducts.com/productdetails.asp?ProductNum=890672



Button with 2m cable

https://www.delcomproducts.com/productdetails.asp?PartNumber=706400



Button with 5m cable

https://www.delcomproducts.com/productdetails.asp?PartNumber=706400-5M

