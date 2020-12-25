# installer for MQTT
# Copyright 2014-2020 Matthew Wall
# Distributed under the terms of the GNU Public License (GPLv3)

from weecfg.extension import ExtensionInstaller

def loader():
    return MQTTInstaller()

class MQTTInstaller(ExtensionInstaller):
    def __init__(self):
        super(MQTTInstaller, self).__init__(
            version="0.30",
            name='mqtt',
            description='Upload weather data to MQTT server. Forked from Matthew Wall\'s work.',
            author="Rich Bell",
            author_email="bellrichm@gmail.com",
            restful_services='user.mqtt.MQTT',
            config={
                'StdRESTful': {
                    'MQTTPublish': {
                        'server_url': 'INSERT_SERVER_URL_HERE'}}},
            files=[('bin/user', ['bin/user/mqttpublish.py'])]
            )
