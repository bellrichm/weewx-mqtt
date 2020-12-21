# pylint: disable=missing-docstring, invalid-name, line-too-long, dangerous-default-value
import copy
import random
import socket
import ssl
import string

import unittest
import mock

import configobj

import paho.mqtt.client as mqtt

import weewx.restx

from user.mqttpublish import MQTTPublishThread

def random_string():
    return ''.join([random.choice(string.ascii_letters + string.digits) for n in range(32)])

def create_topic(skip_upload=False,
                 binding='archive',
                 payload_type='json',
                 append_units_label=True,
                 conversion_type='string',
                 augment_record=True,
                 upload_all=True,
                 retain=False,
                 qos=0,
                 inputs={},
                 templates={}):
    return {
        'skip_upload': skip_upload,
        'binding': binding,
        'type': payload_type,
        'append_units_label': append_units_label,
        'conversion_type':conversion_type,
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
                'weather': create_topic(payload_type='individual')
            },
            'manager_dict': {
                random_string(): random_string()
            },
            'tls': {
                'cert_reqs': 'none',
            }
        }
        site_config = configobj.ConfigObj(site_dict)

        SUT = MQTTPublishThread(None, None, **site_config)
        self.assertEqual(SUT.tls_dict, {'cert_reqs': ssl.CERT_NONE})

    def test_tls_version(self):
        site_dict = {
            'server_url' : random_string,
            'topics': {
                'weather/loop': create_topic(),
                'weather': create_topic(payload_type='individual')
            },
            'manager_dict': {
                random_string(): random_string()
            },
            'tls': {
                'tls_version': 'tls',
            }
        }
        site_config = configobj.ConfigObj(site_dict)

        SUT = MQTTPublishThread(None, None, **site_config)
        self.assertEqual(SUT.tls_dict, {'tls_version': ssl.PROTOCOL_TLS})

    def test_tls_options(self):
        ca_certs = random_string()
        site_dict = {
            'server_url' : random_string,
            'topics': {
                'weather/loop': create_topic(),
                'weather': create_topic(payload_type='individual')
            },
            'manager_dict': {
                random_string(): random_string()
            },
            'tls': {
                'ca_certs': ca_certs
            }
        }
        site_config = configobj.ConfigObj(site_dict)

        SUT = MQTTPublishThread(None, None, **site_config)
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
                'weather': create_topic(payload_type='individual')
            },
            'manager_dict': {
                random_string(): random_string()
            }
        }
        site_config = configobj.ConfigObj(site_dict)

        exception = ConnectionRefusedError("Connect exception.")

        with mock.patch('paho.mqtt.client.Client') as mock_client:
            with mock.patch('user.mqttpublish.time') as mock_time:
                mock_client.return_value = mock_client
                mock_client.connect.side_effect = mock.Mock(side_effect=exception)

                with self.assertRaises(ConnectionError) as error:
                    MQTTPublishThread(None, None, **site_config)

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
                'weather': create_topic(payload_type='individual')
            },
            'manager_dict': {
                random_string(): random_string()
            }
        }
        site_config = configobj.ConfigObj(site_dict)

        exception = ConnectionRefusedError("Connect exception.")
        self.connection_tries = 0

        with mock.patch('paho.mqtt.client.Client') as mock_client:
            with mock.patch('user.mqttpublish.time') as mock_time:
                mock_client.return_value = mock_client
                mock_client.connect.side_effect = mock.Mock(side_effect=exception)
                self.client_connection = mock_client.connect
                mock_time.sleep.side_effect = self.reset_connection_error

                MQTTPublishThread(None, None, **site_config)

                self.assertEqual(mock_client.connect.call_count, self.connection_tries + 1)
                self.assertEqual(mock_time.sleep.call_count, self.connection_tries)

    def test_connection_success(self):
        site_dict = {
            'persist_connection': True,
            'max_tries': random.randint(4, 6),
            'server_url' : 'mqtt://username:password@localhost:1883/',
            'topics': {
                'weather/loop': create_topic(),
                'weather': create_topic(payload_type='individual')
            },
            'manager_dict': {
                random_string(): random_string()
            }
        }
        site_config = configobj.ConfigObj(site_dict)

        self.connection_tries = 0

        with mock.patch('paho.mqtt.client.Client') as mock_client:
            with mock.patch('user.mqttpublish.time') as mock_time:
                mock_client.return_value = mock_client
                MQTTPublishThread(None, None, **site_config)

                self.assertEqual(mock_client.connect.call_count, 1)
                self.assertEqual(mock_time.sleep.call_count, 0)

class TestFilterData(unittest.TestCase):
    observation1 = random_string()
    observation2 = random_string()
    observation3 = random_string()
    observation4 = random_string()

    @classmethod
    def getStandardUnitType_return_value(cls, *args, **kwargs): # match signature pylint: disable=unused-argument
        if args[1] == cls.observation1:
            return 'degree_F', 'group_temperature'
        if args[1] == cls.observation2:
            return 'degree_F', 'group_temperature'
        if args[1] == cls.observation3:
            return 'degree_F', 'group_temperature'
        if args[1] == cls.observation4:
            return 'degree_F', 'group_temperature'

        return None, None

    @classmethod
    def convert_return_value(cls, *args, **kwargs): # match signature pylint: disable=unused-argument
        val_t = args[0]
        return [(val_t[0] - 32) * 5/9]

    def test_upload_all_true(self):
        site_dict = {
            'server_url' : random_string(),
            'topics': {
                'weather/loop': create_topic(),
                'weather': create_topic(payload_type='individual')
            },
            'manager_dict': {
                random_string(): random_string()
            }
        }
        site_config = configobj.ConfigObj(site_dict)

        upload_all = True
        templates = {
            self.observation3: {
                'name': random_string(),
                'format': '%.2f',
                'units': 'degree_C'
            },
        }
        inputs_dict = {
            self.observation1: {
                'name': random_string(),
                'format': '%.2f',
                'units': 'degree_C'
            },
            self.observation2: {
                'format': '%.2f'
            }
        }
        inputs = configobj.ConfigObj(inputs_dict)
        append_units_label = False
        observation2 = round(random.uniform(1, 100), 10)
        observation4 = round(random.uniform(1, 100), 10)
        record = {
            'usUnits': 1.0,
            self.observation2: observation2,
            self.observation4: observation4
        }

        returned_record = copy.deepcopy(record)
        returned_record[self.observation2] = '%.2f' % returned_record[self.observation2]
        returned_record[self.observation4] = str(returned_record[self.observation4])
        returned_record['usUnits'] = str(returned_record['usUnits'])

        returned_templates = copy.deepcopy(templates)
        returned_templates[self.observation2] = inputs_dict[self.observation2]
        returned_templates[self.observation4] = {}
        returned_templates['usUnits'] = {}

        with mock.patch('weewx.units') as mock_units:
            mock_units.getStandardUnitType.side_effect = self.getStandardUnitType_return_value
            mock_units.convert.side_effect = self.convert_return_value
            SUT = MQTTPublishThread(None, None, **site_config)

            filtered_record = SUT.filter_data(upload_all, templates, inputs, append_units_label, 'string', record)

            self.assertEqual(templates, returned_templates)
            self.assertEqual(filtered_record, returned_record)

    def test_upload_all_false(self):
        site_dict = {
            'server_url' : random_string(),
            'topics': {
                'weather/loop': create_topic(),
                'weather': create_topic(payload_type='individual')
            },
            'manager_dict': {
                random_string(): random_string()
            }
        }
        site_config = configobj.ConfigObj(site_dict)

        upload_all = False
        templates = dict()
        inputs_dict = {
            self.observation1: {
                'name': random_string(),
                'format': '%.2f',
                'units': 'degree_C'
            },
            self.observation2: {
                'format': '%.2f'
            }
        }
        inputs = configobj.ConfigObj(inputs_dict)
        append_units_label = False
        observation2 = round(random.uniform(1, 100), 10)
        observation4 = round(random.uniform(1, 100), 10)
        record = {
            'usUnits': 1.0,
            self.observation2: observation2,
            self.observation4: observation4
        }

        returned_record = {}
        returned_record[self.observation2] = '%.2f' % record[self.observation2]

        returned_templates = copy.deepcopy(inputs_dict)

        with mock.patch('weewx.units') as mock_units:
            mock_units.getStandardUnitType.side_effect = self.getStandardUnitType_return_value
            mock_units.convert.side_effect = self.convert_return_value
            SUT = MQTTPublishThread(None, None, **site_config)

            filtered_record = SUT.filter_data(upload_all, templates, inputs, append_units_label, 'string', record)

            self.assertEqual(templates, returned_templates)
            self.assertEqual(filtered_record, returned_record)

    def test_unit_conversion(self):
        site_dict = {
            'server_url' : random_string(),
            'topics': {
                'weather/loop': create_topic(),
                'weather': create_topic(payload_type='individual')
            },
            'manager_dict': {
                random_string(): random_string()
            }
        }
        site_config = configobj.ConfigObj(site_dict)

        upload_all = False
        templates = dict()
        inputs_dict = {
            self.observation1: {
                'name': random_string(),
                'format': '%.2f',
                'units': 'degree_C'
            },
            self.observation2: {
                'format': '%.2f'
            }
        }
        inputs = configobj.ConfigObj(inputs_dict)
        append_units_label = False
        observation1 = round(random.uniform(1, 100), 10)
        observation2 = round(random.uniform(1, 100), 10)
        record = {
            'usUnits': 1.0,
            self.observation1: observation1,
            self.observation2: observation2,
        }

        returned_record = {}
        returned_record[inputs[self.observation1]['name']] = '%.2f' % ((record[self.observation1] - 32) * 5/9)
        returned_record[self.observation2] = '%.2f' % record[self.observation2]

        returned_templates = copy.deepcopy(inputs_dict)

        with mock.patch('weewx.units') as mock_units:
            mock_units.getStandardUnitType.side_effect = self.getStandardUnitType_return_value
            mock_units.convert.side_effect = self.convert_return_value
            SUT = MQTTPublishThread(None, None, **site_config)

            filtered_record = SUT.filter_data(upload_all, templates, inputs, append_units_label, 'string', record)

            self.assertEqual(templates, returned_templates)
            self.assertEqual(filtered_record, returned_record)

    def test_longitude_latitude(self):
        site_dict = {
            'server_url' : random_string(),
            'topics': {
                'weather/loop': create_topic(),
                'weather': create_topic(payload_type='individual')
            },
            'manager_dict': {
                random_string(): random_string()
            }
        }
        site_config = configobj.ConfigObj(site_dict)

        upload_all = True
        templates = {}
        inputs_dict = {}
        inputs = configobj.ConfigObj(inputs_dict)
        append_units_label = False
        record = {
            'usUnits': 1.0,
            'latitude': round(random.uniform(-90, 90), 6),
            'longitude': round(random.uniform(-180, 180), 6),
        }
        returned_record = copy.deepcopy(record)
        returned_record['latitude'] = str(returned_record['latitude'])
        returned_record['longitude'] = str(returned_record['longitude'])
        returned_record['usUnits'] = str(returned_record['usUnits'])
        position = "%s,%s" % (record['latitude'], record['longitude'])
        returned_record['position'] = str(position)

        with mock.patch('weewx.units') as mock_units:
            mock_units.getStandardUnitType.side_effect = self.getStandardUnitType_return_value
            mock_units.convert.side_effect = self.convert_return_value
            SUT = MQTTPublishThread(None, None, **site_config)

            filtered_record = SUT.filter_data(upload_all, templates, inputs, append_units_label, 'string', record)

            self.assertEqual(filtered_record, returned_record)

    def test_altitude_meter(self):
        site_dict = {
            'server_url' : random_string(),
            'topics': {
                'weather/loop': create_topic(),
                'weather': create_topic(payload_type='individual')
            },
            'manager_dict': {
                random_string(): random_string()
            }
        }
        site_config = configobj.ConfigObj(site_dict)

        upload_all = True
        templates = {}
        inputs_dict = {}
        inputs = configobj.ConfigObj(inputs_dict)
        append_units_label = False
        record = {
            'usUnits': 1.0,
            'latitude': round(random.uniform(-90, 90), 6),
            'longitude': round(random.uniform(-180, 180), 6),
            'altitude_meter': round(random.uniform(0, 2000), 6)
        }

        returned_record = copy.deepcopy(record)
        returned_record['latitude'] = str(returned_record['latitude'])
        returned_record['longitude'] = str(returned_record['longitude'])
        returned_record['altitude_meter'] = str(returned_record['altitude_meter'])
        returned_record['usUnits'] = str(returned_record['usUnits'])
        position = "%s,%s,%s" % (record['latitude'], record['longitude'], record['altitude_meter'])
        returned_record['position'] = str(position)

        with mock.patch('weewx.units') as mock_units:
            mock_units.getStandardUnitType.side_effect = self.getStandardUnitType_return_value
            mock_units.convert.side_effect = self.convert_return_value
            SUT = MQTTPublishThread(None, None, **site_config)

            filtered_record = SUT.filter_data(upload_all, templates, inputs, append_units_label, 'string', record)

            self.assertEqual(filtered_record, returned_record)

    def test_altitude_foot(self):
        site_dict = {
            'server_url' : random_string(),
            'topics': {
                'weather/loop': create_topic(),
                'weather': create_topic(payload_type='individual')
            },
            'manager_dict': {
                random_string(): random_string()
            }
        }
        site_config = configobj.ConfigObj(site_dict)

        upload_all = True
        templates = {}
        inputs_dict = {}
        inputs = configobj.ConfigObj(inputs_dict)
        append_units_label = False
        record = {
            'usUnits': 1.0,
            'latitude': round(random.uniform(-90, 90), 6),
            'longitude': round(random.uniform(-180, 180), 6),
            'altitude_foot': round(random.uniform(0, 2000), 6)
        }

        returned_record = copy.deepcopy(record)
        returned_record['latitude'] = str(returned_record['latitude'])
        returned_record['longitude'] = str(returned_record['longitude'])
        returned_record['altitude_foot'] = str(returned_record['altitude_foot'])
        returned_record['usUnits'] = str(returned_record['usUnits'])
        position = "%s,%s,%s" % (record['latitude'], record['longitude'], record['altitude_foot'])
        returned_record['position'] = str(position)

        with mock.patch('weewx.units') as mock_units:
            mock_units.getStandardUnitType.side_effect = self.getStandardUnitType_return_value
            mock_units.convert.side_effect = self.convert_return_value
            SUT = MQTTPublishThread(None, None, **site_config)

            filtered_record = SUT.filter_data(upload_all, templates, inputs, append_units_label, 'string', record)

            self.assertEqual(filtered_record, returned_record)

class TestProcessRecord(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestProcessRecord, self).__init__(*args, **kwargs)
        self.client_connection = None
        self.client_publish = None
        self.connection_tries = 0
        self.max_connection_tries = random.randint(1, 3)

    def reset_connection_error(self, *args, **kwargs): # match signature pylint: disable=unused-argument
        if self.connection_tries >= self.max_connection_tries:
            self.client_connection.side_effect = mock.Mock(side_effect=None)
        self.connection_tries += 1
        return mock.DEFAULT

    def reset_publish_return_value(self, *args, **kwargs): # match signature pylint: disable=unused-argument
        if self.connection_tries >= self.max_connection_tries:
            self.client_publish.return_value = [mqtt.MQTT_ERR_SUCCESS, None]
        self.connection_tries += 1
        return mock.DEFAULT

    def reset_publish_side_effect(self, *args, **kwargs): # match signature pylint: disable=unused-argument
        if self.connection_tries >= self.max_connection_tries:
            self.client_publish.side_effect = None
        self.connection_tries += 1
        return mock.DEFAULT

    def test_connection_error(self):
        mock_manager = mock.Mock()
        max_tries = random.randint(4, 6)
        site_dict = {
            'server_url' : 'mqtt://username:password@localhost:1883/',
            'max_tries': max_tries,
            'topics': {
                'weather/loop': create_topic(),
                'weather': create_topic(payload_type='individual')
            },
            'manager_dict': {
                random_string(): random_string()
            }
        }
        site_config = configobj.ConfigObj(site_dict)

        record = {}

        exception = ConnectionRefusedError("Connect exception.")

        with mock.patch('paho.mqtt.client.Client') as mock_client:
            with mock.patch('user.mqttpublish.time') as mock_time:
                with mock.patch('user.mqttpublish.logerr') as mock_logerr:
                    mock_client.return_value = mock_client
                    mock_client.connect.side_effect = mock.Mock(side_effect=exception)

                    SUT = MQTTPublishThread(None, None, **site_config)

                    SUT.process_record(record, mock_manager)

                    self.assertEqual(mock_client.connect.call_count, max_tries)
                    self.assertEqual(mock_time.sleep.call_count, max_tries)
                    mock_logerr.assert_called_once_with("Could not connect, skipping record: %s" % record)

    def test_connection_recovers(self):
        mock_manager = mock.Mock()
        max_tries = random.randint(4, 6)
        site_dict = {
            'server_url' : 'mqtt://username:password@localhost:1883/',
            'max_tries': max_tries,
            'topics': {
                'weather/loop': create_topic(binding='loop'),
                'weather': create_topic(payload_type='individual', binding='loop')
            },
            'manager_dict': {
                random_string(): random_string()
            }
        }
        site_dict['topics']['weather/loop']['unit_system'] = 'US'
        site_dict['topics']['weather']['unit_system'] = 'US'
        site_config = configobj.ConfigObj(site_dict)

        record = {}

        exception = ConnectionRefusedError("Connect exception.")
        self.connection_tries = 0

        with mock.patch('paho.mqtt.client.Client') as mock_client:
            with mock.patch('user.mqttpublish.time') as mock_time:
                with mock.patch('user.mqttpublish.MQTTPublishThread.get_record'):
                    with mock.patch('weewx.units'):
                        mock_client.return_value = mock_client
                        mock_client.connect.side_effect = mock.Mock(side_effect=exception)
                        self.client_connection = mock_client.connect
                        mock_time.sleep.side_effect = self.reset_connection_error
                        mock_client.publish.return_value = [mqtt.MQTT_ERR_SUCCESS, None]

                        SUT = MQTTPublishThread(None, None, **site_config)

                        SUT.process_record(record, mock_manager)

                        self.assertEqual(mock_client.connect.call_count, self.connection_tries + 1)
                        self.assertEqual(mock_time.sleep.call_count, self.connection_tries)

    def test_connection_success(self):
        mock_manager = mock.Mock()
        max_tries = random.randint(4, 6)
        site_dict = {
            'server_url' : 'mqtt://username:password@localhost:1883/',
            'max_tries': max_tries,
            'topics': {
                'weather/loop': create_topic(binding='loop'),
                'weather': create_topic(payload_type='individual', binding='loop')
            },
            'manager_dict': {
                random_string(): random_string()
            }
        }
        site_dict['topics']['weather/loop']['unit_system'] = 'US'
        site_dict['topics']['weather']['unit_system'] = 'US'
        site_config = configobj.ConfigObj(site_dict)

        record = {}

        with mock.patch('paho.mqtt.client.Client') as mock_client:
            with mock.patch('user.mqttpublish.time') as mock_time:
                with mock.patch('user.mqttpublish.MQTTPublishThread.get_record'):
                    with mock.patch('weewx.units'):
                        mock_client.return_value = mock_client
                        mock_client.publish.return_value = [mqtt.MQTT_ERR_SUCCESS, None]

                        SUT = MQTTPublishThread(None, None, **site_config)

                        SUT.process_record(record, mock_manager)

                        self.assertEqual(mock_client.connect.call_count, 1)
                        self.assertEqual(mock_time.sleep.call_count, 0)

    def test_publish_error_unknown(self):
        mock_manager = mock.Mock()
        max_tries = random.randint(4, 6)
        site_dict = {
            'server_url' : 'mqtt://username:password@localhost:1883/',
            'max_tries': max_tries,
            'topics': {
                'weather/loop': create_topic(binding='loop')
            },
            'manager_dict': {
                random_string(): random_string()
            }
        }
        site_dict['topics']['weather/loop']['unit_system'] = 'US'
        site_dict['persist_connection'] = True
        site_config = configobj.ConfigObj(site_dict)

        record = {}

        with mock.patch('paho.mqtt.client.Client') as mock_client:
            with mock.patch('user.mqttpublish.time') as mock_time:
                with mock.patch('user.mqttpublish.MQTTPublishThread.get_record'):
                    with mock.patch('weewx.units'):
                        mock_client.return_value = mock_client
                        mock_client.publish.return_value = [-1, None]

                        SUT = MQTTPublishThread(None, None, **site_config)

                        with self.assertRaises(weewx.restx.FailedPost) as error:
                            SUT.process_record(record, mock_manager)

                        self.assertEqual(len(error.exception.args), 1)
                        self.assertEqual(error.exception.args[0], "Failed upload after %d tries" % (max_tries,))
                        self.assertEqual(mock_client.publish.call_count, max_tries)
                        self.assertEqual(mock_time.sleep.call_count, max_tries)

    def test_publish_connection_fails(self):
        mock_manager = mock.Mock()
        max_tries = random.randint(4, 6)
        site_dict = {
            'server_url' : 'mqtt://username:password@localhost:1883/',
            'max_tries': max_tries,
            'topics': {
                'weather/loop': create_topic(binding='loop')
            },
            'manager_dict': {
                random_string(): random_string()
            }
        }
        site_dict['topics']['weather/loop']['unit_system'] = 'US'
        site_dict['persist_connection'] = True
        site_config = configobj.ConfigObj(site_dict)

        record = {}

        exception = ConnectionRefusedError("Connect exception.")

        with mock.patch('paho.mqtt.client.Client') as mock_client:
            with mock.patch('user.mqttpublish.time') as mock_time:
                with mock.patch('user.mqttpublish.MQTTPublishThread.get_record'):
                    with mock.patch('weewx.units'):
                        mock_client.return_value = mock_client
                        mock_client.publish.return_value = [mqtt.MQTT_ERR_NO_CONN, None]

                        SUT = MQTTPublishThread(None, None, **site_config)

                        mock_client.connect.side_effect = mock.Mock(side_effect=exception)
                        with self.assertRaises(weewx.restx.FailedPost) as error:
                            SUT.process_record(record, mock_manager)

                        self.assertEqual(len(error.exception.args), 1)
                        self.assertEqual(error.exception.args[0], "Failed upload after %d tries" % (max_tries,))
                        self.assertEqual(mock_client.publish.call_count, max_tries)
                        self.assertEqual(mock_time.sleep.call_count, max_tries)

    def test_publish_connection_recovers(self):
        mock_manager = mock.Mock()
        max_tries = random.randint(4, 6)
        site_dict = {
            'server_url' : 'mqtt://username:password@localhost:1883/',
            'max_tries': max_tries,
            'topics': {
                'weather/loop': create_topic(binding='loop')
            },
            'manager_dict': {
                random_string(): random_string()
            }
        }
        site_dict['topics']['weather/loop']['unit_system'] = 'US'
        site_dict['persist_connection'] = True
        site_config = configobj.ConfigObj(site_dict)

        record = {}

        exception = ConnectionRefusedError("Connect exception.")
        self.connection_tries = 0

        with mock.patch('paho.mqtt.client.Client') as mock_client:
            with mock.patch('user.mqttpublish.time') as mock_time:
                with mock.patch('user.mqttpublish.MQTTPublishThread.get_record'):
                    with mock.patch('weewx.units'):
                        mock_client.return_value = mock_client
                        mock_client.publish.return_value = [mqtt.MQTT_ERR_NO_CONN, None]
                        self.client_publish = mock_client.publish
                        mock_time.sleep.side_effect = self.reset_publish_return_value

                        SUT = MQTTPublishThread(None, None, **site_config)

                        mock_client.connect.side_effect = mock.Mock(side_effect=exception)

                        SUT.process_record(record, mock_manager)

                        self.assertEqual(mock_client.connect.call_count, self.connection_tries + 1)
                        self.assertEqual(mock_time.sleep.call_count, self.connection_tries)

    def test_publish_error(self):
        mock_manager = mock.Mock()
        max_tries = random.randint(4, 6)
        site_dict = {
            'server_url' : 'mqtt://username:password@localhost:1883/',
            'max_tries': max_tries,
            'topics': {
                'weather/loop': create_topic(binding='loop')
            },
            'manager_dict': {
                random_string(): random_string()
            }
        }
        site_dict['topics']['weather/loop']['unit_system'] = 'US'
        site_dict['persist_connection'] = True
        site_config = configobj.ConfigObj(site_dict)

        record = {}

        exception = socket.error("Socket exception.")

        with mock.patch('paho.mqtt.client.Client') as mock_client:
            with mock.patch('user.mqttpublish.time') as mock_time:
                with mock.patch('user.mqttpublish.MQTTPublishThread.get_record'):
                    with mock.patch('weewx.units'):
                        mock_client.return_value = mock_client
                        mock_client.publish.side_effect = mock.Mock(side_effect=exception)

                        SUT = MQTTPublishThread(None, None, **site_config)

                        with self.assertRaises(weewx.restx.FailedPost) as error:
                            SUT.process_record(record, mock_manager)

                        self.assertEqual(len(error.exception.args), 1)
                        self.assertEqual(error.exception.args[0], "Failed upload after %d tries" % (max_tries,))
                        self.assertEqual(mock_client.publish.call_count, max_tries)
                        self.assertEqual(mock_time.sleep.call_count, max_tries)

    def test_publish_recovers(self):
        mock_manager = mock.Mock()
        max_tries = random.randint(4, 6)
        site_dict = {
            'server_url' : 'mqtt://username:password@localhost:1883/',
            'max_tries': max_tries,
            'topics': {
                'weather/loop': create_topic(binding='loop')
            },
            'manager_dict': {
                random_string(): random_string()
            }
        }
        site_dict['topics']['weather/loop']['unit_system'] = 'US'
        site_dict['persist_connection'] = True
        site_config = configobj.ConfigObj(site_dict)

        record = {}

        exception = socket.error("Socket exception.")

        with mock.patch('paho.mqtt.client.Client') as mock_client:
            with mock.patch('user.mqttpublish.time') as mock_time:
                with mock.patch('user.mqttpublish.MQTTPublishThread.get_record'):
                    with mock.patch('weewx.units'):
                        mock_client.return_value = mock_client
                        mock_client.publish.return_value = [mqtt.MQTT_ERR_SUCCESS, None]
                        mock_client.publish.side_effect = mock.Mock(side_effect=exception)
                        self.client_publish = mock_client.publish
                        mock_time.sleep.side_effect = self.reset_publish_side_effect

                        SUT = MQTTPublishThread(None, None, **site_config)

                        SUT.process_record(record, mock_manager)

                        self.assertEqual(mock_client.publish.call_count, self.connection_tries + 1)
                        self.assertEqual(mock_time.sleep.call_count, self.connection_tries)

if __name__ == '__main__':
    #test_suite = unittest.TestSuite()
    #test_suite.addTest(TestProcessRecord('test_new'))
    #unittest.TextTestRunner().run(test_suite)

    unittest.main(exit=False)
