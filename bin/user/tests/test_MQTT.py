# pylint: disable=missing-docstring, invalid-name, line-too-long
import random
import string

import unittest
import mock

import configobj

#import weewx
from weewx import NEW_ARCHIVE_RECORD, NEW_LOOP_PACKET
from user.mqtt import MQTT

def random_string():
    return ''.join([random.choice(string.ascii_letters + string.digits) for n in range(32)])

class TestInitialization(unittest.TestCase):
    def test_example(self):
        mock_StdEngine = mock.Mock()
        server_url = random_string()
        binding = 'archive, loop'

        manager_dict = {
            'foo': 'bar'
        }

        topics = {
            'weather/loop': {
                'skip_upload': False,
                'binding': binding,
                'aggregation': 'aggregate',
                'append_units_label': True,
                'augment_record': True,
                'upload_all': True,
                'retain': False,
                'qos': 0,
                'inputs': {},
                'templates': {}
            },
            'weather': {
                'skip_upload': False,
                'binding': binding,
                'aggregation': 'individual',
                'append_units_label': True,
                'augment_record': True,
                'upload_all': True,
                'retain': False,
                'qos': 0,
                'inputs': {},
                'templates': {}
                }
            }

        config_dict = {
            'StdRESTful': {
                'MQTT': {
                    'server_url': server_url,
                    'binding': binding
                }
            }
        }
        config = configobj.ConfigObj(config_dict)

        site_dict = {
            'server_url' : server_url,
            'binding': binding
        }
        site_config = configobj.ConfigObj(site_dict)

        site_dict_final = {
            'server_url' : server_url,
            'topics': topics,
            'manager_dict': manager_dict
        }
        site_config_final = configobj.ConfigObj(site_dict_final)

        with mock.patch('weewx.restx') as mock_restx:
            with mock.patch('weewx.manager') as mock_manager:
                with mock.patch('weewx.manager.open_manager'):
                    with mock.patch('user.mqtt.MQTT.bind') as mock_bind:
                        with mock.patch('user.mqtt.loginf'):
                            with mock.patch('user.mqtt.MQTTThread') as mock_MQTTThread:
                                mock_restx.get_site_dict.return_value = site_config
                                mock_manager.get_manager_dict_from_config.return_value = manager_dict

                                SUT = MQTT(mock_StdEngine, config)

                                call_args_list = mock_bind.call_args_list

                                self.assertEqual(len(call_args_list), 2)
                                self.assertEqual(call_args_list[0].args[0], NEW_ARCHIVE_RECORD)
                                self.assertEqual(call_args_list[0].args[1], SUT.new_archive_record)
                                self.assertEqual(call_args_list[1].args[0], NEW_LOOP_PACKET)
                                self.assertEqual(call_args_list[1].args[1], SUT.new_loop_packet)

                                mock_MQTTThread.assert_called_once_with(SUT.archive_queue, **site_config_final)


if __name__ == '__main__':
    test_suite = unittest.TestSuite()
    test_suite.addTest(TestInitialization('test_example'))
    unittest.TextTestRunner().run(test_suite)

    #unittest.main(exit=False)
