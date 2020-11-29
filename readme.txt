IMPORTANT, READ THIS!
This was forked from https://github.com/matthewwall/weewx-mqtt, version 0.23, 
commit https://github.com/matthewwall/weewx-mqtt/commit/00e23e804126e107f2dd9553534ae14628bd3c0e

At the time it was intended to be fully compatible but add some functionality I needed.
Namely,
1) The ability to publish to multiple topics.
2) Create a connection at startup and persist it for all publishing.
This resulted in the retry logic being a bit different for publishing failures. 

The changes became large enough that pull request did not seem feasible, so this may diverge more in the future. 
So, unless you realy need the function that has been added, it would be wise to look at using
https://github.com/matthewwall/weewx-mqtt
********************************************************************************************

mqtt - weewx extension that sends data to an MQTT broker
Copyright 2014-2020 Matthew Wall
Distributed under the terms of the GNU Public License (GPLv3)

===============================================================================
Pre-Requisites

Install the MQTT python bindings

For python3:

  sudo pip3 install paho-mqtt

For python2:

  sudo pip install paho-mqtt

===============================================================================
Installation instructions:

1) download

wget -O weewx-mqtt.zip https://github.com/matthewwall/weewx-mqtt/archive/master.zip

2) run the installer:

wee_extension --install weewx-mqtt.zip

3) modify weewx.conf:

[StdRESTful]
    [[MQTT]]
        server_url = mqtt://username:password@example.com:1883

4) restart weewx

sudo /etc/init.d/weewx stop
sudo /etc/init.d/weewx start


===============================================================================
Options

For configuration options and details, see the comments in mqtt.py
