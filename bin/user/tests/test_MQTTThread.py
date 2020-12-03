# pylint: disable=missing-docstring, invalid-name, line-too-long, dangerous-default-value
import random
import ssl
import string

import unittest
import mock

import configobj

from user.mqtt import MQTTThread

def random_string():
    return ''.join([random.choice(string.ascii_letters + string.digits) for n in range(32)])

def create_topic(skip_upload=False,
                 binding='archive',
                 aggregation='aggregate',
                 append_units_label=True,
                 augment_record=True,
                 upload_all=True,
                 retain=False,
                 qos=0,
                 inputs={},
                 templates={}):
    return {
        'skip_upload': skip_upload,
        'binding': binding,
        'aggregation': aggregation,
        'append_units_label': append_units_label,
        'augment_record': augment_record,
        'upload_all': upload_all,
        'retain': retain,
        'qos': qos,
        'inputs': inputs,
        'templates': templates
    }

class TestTLSInitialization(unittest.TestCase):
    def test_certs_required(self):
        site_dict = {
            'server_url' : random_string,
            'topics': {
                'weather/loop': create_topic(),
                'weather': create_topic(aggregation='individual')
            },
            'manager_dict': {
                random_string(): random_string()
            },
            'tls': {
                'cert_reqs': 'none',
            }
        }
        site_config = configobj.ConfigObj(site_dict)

        SUT = MQTTThread(None, **site_config)
        self.assertEqual(SUT.tls_dict, {'cert_reqs': ssl.CERT_NONE})

    def test_tls_version(self):
        site_dict = {
            'server_url' : random_string,
            'topics': {
                'weather/loop': create_topic(),
                'weather': create_topic(aggregation='individual')
            },
            'manager_dict': {
                random_string(): random_string()
            },
            'tls': {
                'tls_version': 'tls',
            }
        }
        site_config = configobj.ConfigObj(site_dict)

        SUT = MQTTThread(None, **site_config)
        self.assertEqual(SUT.tls_dict, {'tls_version': ssl.PROTOCOL_TLS})

    def test_tls_options(self):
        ca_certs = random_string()
        site_dict = {
            'server_url' : random_string,
            'topics': {
                'weather/loop': create_topic(),
                'weather': create_topic(aggregation='individual')
            },
            'manager_dict': {
                random_string(): random_string()
            },
            'tls': {
                'ca_certs': ca_certs
            }
        }
        site_config = configobj.ConfigObj(site_dict)

        SUT = MQTTThread(None, **site_config)
        self.assertEqual(SUT.tls_dict, {'ca_certs': ca_certs})

class TestPersistentConnection(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestPersistentConnection, self).__init__(*args, **kwargs)
        self.client_connection = None
        self.connection_tries = 0
        self.max_connection_tries = random.randint(1, 3)

    def reset_connection_error(self, *args, **kwargs): # match signature pylint: disable=unused-argument
        if self.connection_tries >= self.max_connection_tries:
            self.client_connection.side_effect = mock.Mock(side_effect=None)
        self.connection_tries += 1
        return mock.DEFAULT

    def test_connection_error(self):
        max_tries = random.randint(4, 6)
        site_dict = {
            'persist_connection': True,
            'max_tries': max_tries,
            'server_url' : 'mqtt://username:password@localhost:1883/',
            'topics': {
                'weather/loop': create_topic(),
                'weather': create_topic(aggregation='individual')
            },
            'manager_dict': {
                random_string(): random_string()
            }
        }
        site_config = configobj.ConfigObj(site_dict)

        exception = ConnectionRefusedError("Connect exception.")

        with mock.patch('paho.mqtt.client.Client') as mock_client:
            with mock.patch('user.mqtt.time') as mock_time:
                mock_client.return_value = mock_client
                mock_client.connect.side_effect = mock.Mock(side_effect=exception)

                with self.assertRaises(ConnectionError) as error:
                    MQTTThread(None, **site_config)

                self.assertEqual(len(error.exception.args), 0)
                self.assertEqual(mock_client.connect.call_count, max_tries)
                self.assertEqual(mock_time.sleep.call_count, max_tries)

    def test_connection_recovers(self):
        site_dict = {
            'persist_connection': True,
            'max_tries': random.randint(4, 6),
            'server_url' : 'mqtt://username:password@localhost:1883/',
            'topics': {
                'weather/loop': create_topic(),
                'weather': create_topic(aggregation='individual')
            },
            'manager_dict': {
                random_string(): random_string()
            }
        }
        site_config = configobj.ConfigObj(site_dict)

        exception = ConnectionRefusedError("Connect exception.")
        self.connection_tries = 0

        with mock.patch('paho.mqtt.client.Client') as mock_client:
            with mock.patch('user.mqtt.time') as mock_time:
                mock_client.return_value = mock_client
                mock_client.connect.side_effect = mock.Mock(side_effect=exception)
                self.client_connection = mock_client.connect
                mock_time.sleep.side_effect = self.reset_connection_error

                MQTTThread(None, **site_config)

                self.assertEqual(mock_client.connect.call_count, self.connection_tries + 1)
                self.assertEqual(mock_time.sleep.call_count, self.connection_tries)

    def test_connection_success(self):
        site_dict = {
            'persist_connection': True,
            'max_tries': random.randint(4, 6),
            'server_url' : 'mqtt://username:password@localhost:1883/',
            'topics': {
                'weather/loop': create_topic(),
                'weather': create_topic(aggregation='individual')
            },
            'manager_dict': {
                random_string(): random_string()
            }
        }
        site_config = configobj.ConfigObj(site_dict)

        self.connection_tries = 0

        with mock.patch('paho.mqtt.client.Client') as mock_client:
            with mock.patch('user.mqtt.time') as mock_time:
                mock_client.return_value = mock_client
                MQTTThread(None, **site_config)

                self.assertEqual(mock_client.connect.call_count, 1)
                self.assertEqual(mock_time.sleep.call_count, 0)

class TestFilterData(unittest.TestCase):
    observation1 = random_string()
    observation2 = random_string()
    observation3 = random_string()

    @classmethod
    def getStandardUnitType_return_value(cls, *args, **kwargs): # match signature pylint: disable=unused-argument
        if args[1] == cls.observation1:
            return 'degree_F', 'group_temperature'
        if args[1] == cls.observation2:
            return 'degree_F', 'group_temperature'
        if args[1] == cls.observation3:
            return 'degree_F', 'group_temperature'            

        return None, None

    @classmethod
    def convert_return_value(cls, *args, **kwargs): # match signature pylint: disable=unused-argument
        val_t = args[0]
        return [(val_t[0] - 32) * 5/9]

    def test_example(self):
        site_dict = {
            'server_url' : random_string(),
            'topics': {
                'weather/loop': create_topic(),
                'weather': create_topic(aggregation='individual')
            },
            'manager_dict': {
                random_string(): random_string()
            }
        }
        site_config = configobj.ConfigObj(site_dict)

        upload_all = True
        templates = dict()
        inputs_dict = {
            self.observation1: {
                'name': 'bar',
                'format': '%.2f',
                'units': 'degree_C'
            },
            self.observation2: {
                'format': '%.2f'
            }
        }
        inputs = configobj.ConfigObj(inputs_dict)
        append_units_label = True
        observation1 = round(random.uniform(1, 100), 10)
        observation2 = round(random.uniform(1, 100), 10)
        observation3 = round(random.uniform(1, 100), 10)
        record = {
            'usUnits': 1,
            self.observation1: observation1,
            self.observation2: observation2,
            self.observation3: observation3,
            'latitude': round(random.uniform(-90, 90), 10),
            'longitude': round(random.uniform(-180, 180), 10),
            'altitude_meter': round(random.uniform(0, 2000), 10),
            'altitude_foot': round(random.uniform(0, 2000), 10)
        }

        with mock.patch('weewx.units') as mock_units:
            mock_units.getStandardUnitType.side_effect = self.getStandardUnitType_return_value
            mock_units.convert.side_effect = self.convert_return_value
            SUT = MQTTThread(None, **site_config)

            filtered_record = SUT.filter_data(upload_all, templates, inputs, append_units_label, record)
            print(record)
            print(filtered_record)
            #print(templates)
            print("done")

if __name__ == '__main__':
    #test_suite = unittest.TestSuite()
    #test_suite.addTest(TestFilterData('test_new'))
    #unittest.TextTestRunner().run(test_suite)

    unittest.main(exit=False)
