# pylint: disable=missing-docstring, invalid-name, line-too-long, dangerous-default-value, too-many-lines
import copy
import random
import string

import unittest
import mock

import configobj

#import weewx
from weewx import NEW_ARCHIVE_RECORD, NEW_LOOP_PACKET
from user.mqtt import MQTTPublish

def random_string():
    return ''.join([random.choice(string.ascii_letters + string.digits) for n in range(32)])

class TestInitialization(unittest.TestCase):
    @staticmethod
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
            'conversion_type': conversion_type,
            'augment_record': augment_record,
            'upload_all': upload_all,
            'retain': retain,
            'qos': qos,
            'inputs': inputs,
            'templates': templates
        }

    def test_minimum_configuration(self):
        mock_StdEngine = mock.Mock()
        server_url = random_string()

        config_dict = {
            'StdRESTful': {
                'MQTTPublish': {
                    'server_url': server_url,
                }
            }
        }
        config = configobj.ConfigObj(config_dict)

        manager_dict = {
            random_string(): random_string()
        }

        topics = {
            'weather/loop': self.create_topic(),
            'weather': self.create_topic(payload_type='individual')
            }

        site_dict = copy.deepcopy(config_dict['StdRESTful']['MQTTPublish'])
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
                    with mock.patch('user.mqtt.MQTTPublish.bind') as mock_bind:
                        with mock.patch('user.mqtt.loginf'):
                            with mock.patch('user.mqtt.MQTTPublishThread') as mock_MQTTThread:
                                mock_restx.get_site_dict.return_value = site_config
                                mock_manager.get_manager_dict_from_config.return_value = manager_dict

                                SUT = MQTTPublish(mock_StdEngine, config)

                                mock_manager.get_manager_dict_from_config.assert_called_once_with(config, 'wx_binding')
                                mock_manager.open_manager.assert_called_once_with(manager_dict)

                                call_args_list = mock_bind.call_args_list
                                self.assertEqual(len(call_args_list), 1)
                                self.assertEqual(call_args_list[0].args[0], NEW_ARCHIVE_RECORD)
                                self.assertEqual(call_args_list[0].args[1], SUT.new_archive_record)

                                mock_MQTTThread.assert_called_once_with('MQTTPublish', SUT.archive_queue, **site_config_final)

    def test_topic(self):
        mock_StdEngine = mock.Mock()
        server_url = random_string()
        topic = random_string()

        config_dict = {
            'StdRESTful': {
                'MQTTPublish': {
                    'server_url': server_url,
                    'topic': topic
                }
            }
        }
        config = configobj.ConfigObj(config_dict)

        manager_dict = {
            random_string(): random_string()
        }

        topics = {
            topic + '/loop': self.create_topic(),
            topic: self.create_topic(payload_type='individual')
            }

        site_dict = copy.deepcopy(config_dict['StdRESTful']['MQTTPublish'])
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
                    with mock.patch('user.mqtt.MQTTPublish.bind'):
                        with mock.patch('user.mqtt.loginf'):
                            with mock.patch('user.mqtt.MQTTPublishThread') as mock_MQTTThread:
                                mock_restx.get_site_dict.return_value = site_config
                                mock_manager.get_manager_dict_from_config.return_value = manager_dict

                                SUT = MQTTPublish(mock_StdEngine, config)

                                mock_MQTTThread.assert_called_once_with('MQTTPublish', SUT.archive_queue, **site_config_final)

    def test_binding(self):
        mock_StdEngine = mock.Mock()
        server_url = random_string()

        config_dict = {
            'StdRESTful': {
                'MQTTPublish': {
                    'server_url': server_url,
                    'binding': 'archive, loop'
                }
            }
        }
        config = configobj.ConfigObj(config_dict)

        manager_dict = {
            random_string(): random_string()
        }

        topics = {
            'weather/loop': self.create_topic(binding='archive, loop'),
            'weather': self.create_topic(payload_type='individual', binding='archive, loop')
            }

        site_dict = copy.deepcopy(config_dict['StdRESTful']['MQTTPublish'])
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
                    with mock.patch('user.mqtt.MQTTPublish.bind') as mock_bind:
                        with mock.patch('user.mqtt.loginf'):
                            with mock.patch('user.mqtt.MQTTPublishThread') as mock_MQTTThread:
                                mock_restx.get_site_dict.return_value = site_config
                                mock_manager.get_manager_dict_from_config.return_value = manager_dict

                                SUT = MQTTPublish(mock_StdEngine, config)

                                call_args_list = mock_bind.call_args_list
                                self.assertEqual(len(call_args_list), 2)
                                self.assertEqual(call_args_list[0].args[0], NEW_ARCHIVE_RECORD)
                                self.assertEqual(call_args_list[0].args[1], SUT.new_archive_record)
                                self.assertEqual(call_args_list[1].args[0], NEW_LOOP_PACKET)
                                self.assertEqual(call_args_list[1].args[1], SUT.new_loop_packet)

                                mock_MQTTThread.assert_called_once_with('MQTTPublish', SUT.archive_queue, **site_config_final)

    def test_aggregation(self):
        mock_StdEngine = mock.Mock()
        server_url = random_string()

        config_dict = {
            'StdRESTful': {
                'MQTTPublish': {
                    'server_url': server_url,
                    'aggregation': 'individual'
                }
            }
        }
        config = configobj.ConfigObj(config_dict)

        manager_dict = {
            random_string(): random_string()
        }

        topics = {
            'weather': self.create_topic(payload_type='individual')
            }

        site_dict = copy.deepcopy(config_dict['StdRESTful']['MQTTPublish'])
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
                    with mock.patch('user.mqtt.MQTTPublish.bind'):
                        with mock.patch('user.mqtt.loginf'):
                            with mock.patch('user.mqtt.MQTTPublishThread') as mock_MQTTThread:
                                mock_restx.get_site_dict.return_value = site_config
                                mock_manager.get_manager_dict_from_config.return_value = manager_dict

                                SUT = MQTTPublish(mock_StdEngine, config)

                                mock_MQTTThread.assert_called_once_with('MQTTPublish', SUT.archive_queue, **site_config_final)

    def test_skip_upload(self):
        mock_StdEngine = mock.Mock()
        server_url = random_string()

        config_dict = {
            'StdRESTful': {
                'MQTTPublish': {
                    'server_url': server_url,
                    'skip_upload': True
                }
            }
        }
        config = configobj.ConfigObj(config_dict)

        manager_dict = {
            random_string(): random_string()
        }

        topics = {
            'weather/loop': self.create_topic(skip_upload=True),
            'weather': self.create_topic(payload_type='individual', skip_upload=True)
            }

        site_dict = copy.deepcopy(config_dict['StdRESTful']['MQTTPublish'])
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
                    with mock.patch('user.mqtt.MQTTPublish.bind'):
                        with mock.patch('user.mqtt.loginf'):
                            with mock.patch('user.mqtt.MQTTPublishThread') as mock_MQTTThread:
                                mock_restx.get_site_dict.return_value = site_config
                                mock_manager.get_manager_dict_from_config.return_value = manager_dict

                                SUT = MQTTPublish(mock_StdEngine, config)

                                mock_MQTTThread.assert_called_once_with('MQTTPublish', SUT.archive_queue, **site_config_final)

    def test_obs_to_upload(self):
        mock_StdEngine = mock.Mock()
        server_url = random_string()

        config_dict = {
            'StdRESTful': {
                'MQTTPublish': {
                    'server_url': server_url,
                    'obs_to_upload': 'none'
                }
            }
        }
        config = configobj.ConfigObj(config_dict)

        manager_dict = {
            random_string(): random_string()
        }

        topics = {
            'weather/loop': self.create_topic(upload_all=False),
            'weather': self.create_topic(payload_type='individual', upload_all=False)
            }

        site_dict = copy.deepcopy(config_dict['StdRESTful']['MQTTPublish'])
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
                    with mock.patch('user.mqtt.MQTTPublish.bind'):
                        with mock.patch('user.mqtt.loginf'):
                            with mock.patch('user.mqtt.MQTTPublishThread') as mock_MQTTThread:
                                mock_restx.get_site_dict.return_value = site_config
                                mock_manager.get_manager_dict_from_config.return_value = manager_dict

                                SUT = MQTTPublish(mock_StdEngine, config)

                                mock_MQTTThread.assert_called_once_with('MQTTPublish', SUT.archive_queue, **site_config_final)

    def test_append_units_label(self):
        mock_StdEngine = mock.Mock()
        server_url = random_string()

        config_dict = {
            'StdRESTful': {
                'MQTTPublish': {
                    'server_url': server_url,
                    'append_units_label': False
                }
            }
        }
        config = configobj.ConfigObj(config_dict)

        manager_dict = {
            random_string(): random_string()
        }

        topics = {
            'weather/loop': self.create_topic(append_units_label=False),
            'weather': self.create_topic(payload_type='individual', append_units_label=False)
            }

        site_dict = copy.deepcopy(config_dict['StdRESTful']['MQTTPublish'])
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
                    with mock.patch('user.mqtt.MQTTPublish.bind'):
                        with mock.patch('user.mqtt.loginf'):
                            with mock.patch('user.mqtt.MQTTPublishThread') as mock_MQTTThread:
                                mock_restx.get_site_dict.return_value = site_config
                                mock_manager.get_manager_dict_from_config.return_value = manager_dict

                                SUT = MQTTPublish(mock_StdEngine, config)

                                mock_MQTTThread.assert_called_once_with('MQTTPublish', SUT.archive_queue, **site_config_final)

    def test_retain(self):
        mock_StdEngine = mock.Mock()
        server_url = random_string()

        config_dict = {
            'StdRESTful': {
                'MQTTPublish': {
                    'server_url': server_url,
                    'retain': True
                }
            }
        }
        config = configobj.ConfigObj(config_dict)

        manager_dict = {
            random_string(): random_string()
        }

        topics = {
            'weather/loop': self.create_topic(retain=True),
            'weather': self.create_topic(payload_type='individual', retain=True)
            }

        site_dict = copy.deepcopy(config_dict['StdRESTful']['MQTTPublish'])
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
                    with mock.patch('user.mqtt.MQTTPublish.bind'):
                        with mock.patch('user.mqtt.loginf'):
                            with mock.patch('user.mqtt.MQTTPublishThread') as mock_MQTTThread:
                                mock_restx.get_site_dict.return_value = site_config
                                mock_manager.get_manager_dict_from_config.return_value = manager_dict

                                SUT = MQTTPublish(mock_StdEngine, config)


                                mock_MQTTThread.assert_called_once_with('MQTTPublish', SUT.archive_queue, **site_config_final)

    def test_augment_record(self):
        mock_StdEngine = mock.Mock()
        server_url = random_string()

        config_dict = {
            'StdRESTful': {
                'MQTTPublish': {
                    'server_url': server_url,
                    'augment_record': False
                }
            }
        }
        config = configobj.ConfigObj(config_dict)

        topics = {
            'weather/loop': self.create_topic(augment_record=False),
            'weather': self.create_topic(payload_type='individual', augment_record=False)
            }

        site_dict = copy.deepcopy(config_dict['StdRESTful']['MQTTPublish'])
        site_config = configobj.ConfigObj(site_dict)

        site_dict_final = {
            'server_url' : server_url,
            'topics': topics
        }
        site_config_final = configobj.ConfigObj(site_dict_final)

        with mock.patch('weewx.restx') as mock_restx:
            with mock.patch('weewx.manager') as mock_manager:
                with mock.patch('weewx.manager.open_manager'):
                    with mock.patch('user.mqtt.MQTTPublish.bind'):
                        with mock.patch('user.mqtt.loginf'):
                            with mock.patch('user.mqtt.MQTTPublishThread') as mock_MQTTThread:
                                mock_restx.get_site_dict.return_value = site_config

                                SUT = MQTTPublish(mock_StdEngine, config)

                                mock_manager.get_manager_dict_from_config.assert_not_called()
                                mock_manager.open_manager.assert_not_called()

                                mock_MQTTThread.assert_called_once_with('MQTTPublish', SUT.archive_queue, **site_config_final)

    def test_qos(self):
        mock_StdEngine = mock.Mock()
        server_url = random_string()

        config_dict = {
            'StdRESTful': {
                'MQTTPublish': {
                    'server_url': server_url,
                    'qos': 2
                }
            }
        }
        config = configobj.ConfigObj(config_dict)

        manager_dict = {
            random_string(): random_string()
        }

        topics = {
            'weather/loop': self.create_topic(qos=2),
            'weather': self.create_topic(payload_type='individual', qos=2)
            }

        site_dict = copy.deepcopy(config_dict['StdRESTful']['MQTTPublish'])
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
                    with mock.patch('user.mqtt.MQTTPublish.bind'):
                        with mock.patch('user.mqtt.loginf'):
                            with mock.patch('user.mqtt.MQTTPublishThread') as mock_MQTTThread:
                                mock_restx.get_site_dict.return_value = site_config
                                mock_manager.get_manager_dict_from_config.return_value = manager_dict

                                SUT = MQTTPublish(mock_StdEngine, config)

                                mock_MQTTThread.assert_called_once_with('MQTTPublish', SUT.archive_queue, **site_config_final)

    def test_unit_system(self):
        mock_StdEngine = mock.Mock()
        server_url = random_string()

        config_dict = {
            'StdRESTful': {
                'MQTTPublish': {
                    'server_url': server_url,
                    'unit_system': 'US'
                }
            }
        }
        config = configobj.ConfigObj(config_dict)

        manager_dict = {
            random_string(): random_string()
        }

        topics = {
            'weather/loop': self.create_topic(),
            'weather': self.create_topic(payload_type='individual')
            }
        topics['weather/loop']['unit_system'] = 1
        topics['weather']['unit_system'] = 1

        site_dict = copy.deepcopy(config_dict['StdRESTful']['MQTTPublish'])
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
                    with mock.patch('user.mqtt.MQTTPublish.bind'):
                        with mock.patch('user.mqtt.loginf'):
                            with mock.patch('user.mqtt.MQTTPublishThread') as mock_MQTTThread:
                                mock_restx.get_site_dict.return_value = site_config
                                mock_manager.get_manager_dict_from_config.return_value = manager_dict

                                SUT = MQTTPublish(mock_StdEngine, config)

                                mock_MQTTThread.assert_called_once_with('MQTTPublish', SUT.archive_queue, **site_config_final)

    def test_inputs(self):
        mock_StdEngine = mock.Mock()
        server_url = random_string()

        inputs = {
            random_string(): random_string()
        }

        config_dict = {
            'StdRESTful': {
                'MQTTPublish': {
                    'server_url': server_url,
                    'inputs': inputs
                }
            }
        }
        config = configobj.ConfigObj(config_dict)

        manager_dict = {
            random_string(): random_string()
        }

        topics = {
            'weather/loop': self.create_topic(inputs=inputs),
            'weather': self.create_topic(payload_type='individual', inputs=inputs)
            }

        site_dict = copy.deepcopy(config_dict['StdRESTful']['MQTTPublish'])
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
                    with mock.patch('user.mqtt.MQTTPublish.bind'):
                        with mock.patch('user.mqtt.loginf'):
                            with mock.patch('user.mqtt.MQTTPublishThread') as mock_MQTTThread:
                                mock_restx.get_site_dict.return_value = site_config
                                mock_manager.get_manager_dict_from_config.return_value = manager_dict

                                SUT = MQTTPublish(mock_StdEngine, config)

                                mock_MQTTThread.assert_called_once_with('MQTTPublish', SUT.archive_queue, **site_config_final)

    def test_topics_minimum_configuration(self):
        mock_StdEngine = mock.Mock()
        server_url = random_string()
        topic = random_string()

        config_dict = {
            'StdRESTful': {
                'MQTTPublish': {
                    'server_url': server_url,
                    'topics': {
                        topic: {}
                    }
                }
            }
        }
        config = configobj.ConfigObj(config_dict)

        manager_dict = {
            random_string(): random_string()
        }

        topics = {
            topic: self.create_topic()
            }

        site_dict = copy.deepcopy(config_dict['StdRESTful']['MQTTPublish'])
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
                    with mock.patch('user.mqtt.MQTTPublish.bind'):
                        with mock.patch('user.mqtt.loginf'):
                            with mock.patch('user.mqtt.MQTTPublishThread') as mock_MQTTThread:
                                mock_restx.get_site_dict.return_value = site_config
                                mock_manager.get_manager_dict_from_config.return_value = manager_dict

                                SUT = MQTTPublish(mock_StdEngine, config)

                                mock_MQTTThread.assert_called_once_with('MQTTPublish', SUT.archive_queue, **site_config_final)

    def test_topics_binding(self):
        mock_StdEngine = mock.Mock()
        server_url = random_string()
        topic = random_string()

        config_dict = {
            'StdRESTful': {
                'MQTTPublish': {
                    'server_url': server_url,
                    'topics': {
                        topic: {
                            'binding': 'archive, loop'
                        }
                    }
                }
            }
        }
        config = configobj.ConfigObj(config_dict)

        manager_dict = {
            random_string(): random_string()
        }

        topics = {
            topic: self.create_topic(binding='archive, loop')
        }

        site_dict = copy.deepcopy(config_dict['StdRESTful']['MQTTPublish'])
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
                    with mock.patch('user.mqtt.MQTTPublish.bind') as mock_bind:
                        with mock.patch('user.mqtt.loginf'):
                            with mock.patch('user.mqtt.MQTTPublishThread') as mock_MQTTThread:
                                mock_restx.get_site_dict.return_value = site_config
                                mock_manager.get_manager_dict_from_config.return_value = manager_dict

                                SUT = MQTTPublish(mock_StdEngine, config)

                                call_args_list = mock_bind.call_args_list
                                self.assertEqual(len(call_args_list), 2)
                                self.assertEqual(call_args_list[0].args[0], NEW_ARCHIVE_RECORD)
                                self.assertEqual(call_args_list[0].args[1], SUT.new_archive_record)
                                self.assertEqual(call_args_list[1].args[0], NEW_LOOP_PACKET)
                                self.assertEqual(call_args_list[1].args[1], SUT.new_loop_packet)

                                mock_MQTTThread.assert_called_once_with('MQTTPublish', SUT.archive_queue, **site_config_final)

    def test_topics_type_individual(self):
        mock_StdEngine = mock.Mock()
        server_url = random_string()
        topic = random_string()

        config_dict = {
            'StdRESTful': {
                'MQTTPublish': {
                    'server_url': server_url,
                    'topics': {
                        topic: {
                            'type': 'individual'
                        }
                    }
                }
            }
        }
        config = configobj.ConfigObj(config_dict)

        manager_dict = {
            random_string(): random_string()
        }

        topics = {
            topic: self.create_topic(payload_type='individual')
        }

        site_dict = copy.deepcopy(config_dict['StdRESTful']['MQTTPublish'])
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
                    with mock.patch('user.mqtt.MQTTPublish.bind'):
                        with mock.patch('user.mqtt.loginf'):
                            with mock.patch('user.mqtt.MQTTPublishThread') as mock_MQTTThread:
                                mock_restx.get_site_dict.return_value = site_config
                                mock_manager.get_manager_dict_from_config.return_value = manager_dict

                                SUT = MQTTPublish(mock_StdEngine, config)

                                mock_MQTTThread.assert_called_once_with('MQTTPublish', SUT.archive_queue, **site_config_final)

    def test_topicsskip_upload(self):
        mock_StdEngine = mock.Mock()
        server_url = random_string()
        topic = random_string()

        config_dict = {
            'StdRESTful': {
                'MQTTPublish': {
                    'server_url': server_url,
                    'topics': {
                        topic: {
                            'skip_upload': True
                        }
                    }
                }
            }
        }
        config = configobj.ConfigObj(config_dict)

        manager_dict = {
            random_string(): random_string()
        }

        topics = {
            topic: self.create_topic(skip_upload=True)
        }

        site_dict = copy.deepcopy(config_dict['StdRESTful']['MQTTPublish'])
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
                    with mock.patch('user.mqtt.MQTTPublish.bind'):
                        with mock.patch('user.mqtt.loginf'):
                            with mock.patch('user.mqtt.MQTTPublishThread') as mock_MQTTThread:
                                mock_restx.get_site_dict.return_value = site_config
                                mock_manager.get_manager_dict_from_config.return_value = manager_dict

                                SUT = MQTTPublish(mock_StdEngine, config)

                                mock_MQTTThread.assert_called_once_with('MQTTPublish', SUT.archive_queue, **site_config_final)

    def test_topicsobs_to_upload(self):
        mock_StdEngine = mock.Mock()
        server_url = random_string()
        topic = random_string()

        config_dict = {
            'StdRESTful': {
                'MQTTPublish': {
                    'server_url': server_url,
                    'topics': {
                        topic: {
                            'obs_to_upload': 'none'
                        }
                    }
                }
            }
        }
        config = configobj.ConfigObj(config_dict)

        manager_dict = {
            random_string(): random_string()
        }

        topics = {
            topic: self.create_topic(upload_all=False)
        }

        site_dict = copy.deepcopy(config_dict['StdRESTful']['MQTTPublish'])
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
                    with mock.patch('user.mqtt.MQTTPublish.bind'):
                        with mock.patch('user.mqtt.loginf'):
                            with mock.patch('user.mqtt.MQTTPublishThread') as mock_MQTTThread:
                                mock_restx.get_site_dict.return_value = site_config
                                mock_manager.get_manager_dict_from_config.return_value = manager_dict

                                SUT = MQTTPublish(mock_StdEngine, config)

                                mock_MQTTThread.assert_called_once_with('MQTTPublish', SUT.archive_queue, **site_config_final)

    def test_topicsappend_units_label(self):
        mock_StdEngine = mock.Mock()
        server_url = random_string()
        topic = random_string()

        config_dict = {
            'StdRESTful': {
                'MQTTPublish': {
                    'server_url': server_url,
                    'topics': {
                        topic: {
                            'append_units_label': False
                        }
                    }
                }
            }
        }
        config = configobj.ConfigObj(config_dict)

        manager_dict = {
            random_string(): random_string()
        }

        topics = {
            topic: self.create_topic(append_units_label=False)
        }

        site_dict = copy.deepcopy(config_dict['StdRESTful']['MQTTPublish'])
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
                    with mock.patch('user.mqtt.MQTTPublish.bind'):
                        with mock.patch('user.mqtt.loginf'):
                            with mock.patch('user.mqtt.MQTTPublishThread') as mock_MQTTThread:
                                mock_restx.get_site_dict.return_value = site_config
                                mock_manager.get_manager_dict_from_config.return_value = manager_dict

                                SUT = MQTTPublish(mock_StdEngine, config)

                                mock_MQTTThread.assert_called_once_with('MQTTPublish', SUT.archive_queue, **site_config_final)

    def test_topicsretain(self):
        mock_StdEngine = mock.Mock()
        server_url = random_string()
        topic = random_string()

        config_dict = {
            'StdRESTful': {
                'MQTTPublish': {
                    'server_url': server_url,
                    'topics': {
                        topic: {
                            'retain': True
                        }
                    }
                }
            }
        }
        config = configobj.ConfigObj(config_dict)

        manager_dict = {
            random_string(): random_string()
        }

        topics = {
            topic: self.create_topic(retain=True)
        }

        site_dict = copy.deepcopy(config_dict['StdRESTful']['MQTTPublish'])
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
                    with mock.patch('user.mqtt.MQTTPublish.bind'):
                        with mock.patch('user.mqtt.loginf'):
                            with mock.patch('user.mqtt.MQTTPublishThread') as mock_MQTTThread:
                                mock_restx.get_site_dict.return_value = site_config
                                mock_manager.get_manager_dict_from_config.return_value = manager_dict

                                SUT = MQTTPublish(mock_StdEngine, config)


                                mock_MQTTThread.assert_called_once_with('MQTTPublish', SUT.archive_queue, **site_config_final)

    def test_topicsaugment_record(self):
        mock_StdEngine = mock.Mock()
        server_url = random_string()
        topic = random_string()

        config_dict = {
            'StdRESTful': {
                'MQTTPublish': {
                    'server_url': server_url,
                    'topics': {
                        topic: {
                            'augment_record': False
                        }
                    }
                }
            }
        }
        config = configobj.ConfigObj(config_dict)

        topics = {
            topic: self.create_topic(augment_record=False)
        }

        site_dict = copy.deepcopy(config_dict['StdRESTful']['MQTTPublish'])
        site_config = configobj.ConfigObj(site_dict)

        site_dict_final = {
            'server_url' : server_url,
            'topics': topics
        }
        site_config_final = configobj.ConfigObj(site_dict_final)

        with mock.patch('weewx.restx') as mock_restx:
            with mock.patch('weewx.manager') as mock_manager:
                with mock.patch('weewx.manager.open_manager'):
                    with mock.patch('user.mqtt.MQTTPublish.bind'):
                        with mock.patch('user.mqtt.loginf'):
                            with mock.patch('user.mqtt.MQTTPublishThread') as mock_MQTTThread:
                                mock_restx.get_site_dict.return_value = site_config

                                SUT = MQTTPublish(mock_StdEngine, config)

                                mock_manager.get_manager_dict_from_config.assert_not_called()
                                mock_manager.open_manager.assert_not_called()

                                mock_MQTTThread.assert_called_once_with('MQTTPublish', SUT.archive_queue, **site_config_final)

    def test_topicsqos(self):
        mock_StdEngine = mock.Mock()
        server_url = random_string()
        topic = random_string()

        config_dict = {
            'StdRESTful': {
                'MQTTPublish': {
                    'server_url': server_url,
                    'topics': {
                        topic: {
                            'qos': 2
                        }
                    }
                }
            }
        }
        config = configobj.ConfigObj(config_dict)

        manager_dict = {
            random_string(): random_string()
        }

        topics = {
            topic: self.create_topic(qos=2)
        }

        site_dict = copy.deepcopy(config_dict['StdRESTful']['MQTTPublish'])
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
                    with mock.patch('user.mqtt.MQTTPublish.bind'):
                        with mock.patch('user.mqtt.loginf'):
                            with mock.patch('user.mqtt.MQTTPublishThread') as mock_MQTTThread:
                                mock_restx.get_site_dict.return_value = site_config
                                mock_manager.get_manager_dict_from_config.return_value = manager_dict

                                SUT = MQTTPublish(mock_StdEngine, config)

                                mock_MQTTThread.assert_called_once_with('MQTTPublish', SUT.archive_queue, **site_config_final)

    def test_topicsunit_system(self):
        mock_StdEngine = mock.Mock()
        server_url = random_string()
        topic = random_string()

        config_dict = {
            'StdRESTful': {
                'MQTTPublish': {
                    'server_url': server_url,
                    'topics': {
                        topic: {
                            'unit_system': 'US'
                        }
                    }
                }
            }
        }
        config = configobj.ConfigObj(config_dict)

        manager_dict = {
            random_string(): random_string()
        }

        topics = {
            topic: self.create_topic()
        }
        topics[topic]['unit_system'] = 1

        site_dict = copy.deepcopy(config_dict['StdRESTful']['MQTTPublish'])
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
                    with mock.patch('user.mqtt.MQTTPublish.bind'):
                        with mock.patch('user.mqtt.loginf'):
                            with mock.patch('user.mqtt.MQTTPublishThread') as mock_MQTTThread:
                                mock_restx.get_site_dict.return_value = site_config
                                mock_manager.get_manager_dict_from_config.return_value = manager_dict

                                SUT = MQTTPublish(mock_StdEngine, config)

                                mock_MQTTThread.assert_called_once_with('MQTTPublish', SUT.archive_queue, **site_config_final)

    def test_topicsinputs(self):
        mock_StdEngine = mock.Mock()
        server_url = random_string()
        topic = random_string()

        inputs = {
            random_string(): random_string()
        }

        config_dict = {
            'StdRESTful': {
                'MQTTPublish': {
                    'server_url': server_url,
                    'topics': {
                        topic: {
                            'inputs': inputs
                        }
                    }
                }
            }
        }
        config = configobj.ConfigObj(config_dict)

        manager_dict = {
            random_string(): random_string()
        }

        topics = {
            topic: self.create_topic(inputs=inputs)
        }

        site_dict = copy.deepcopy(config_dict['StdRESTful']['MQTTPublish'])
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
                    with mock.patch('user.mqtt.MQTTPublish.bind'):
                        with mock.patch('user.mqtt.loginf'):
                            with mock.patch('user.mqtt.MQTTPublishThread') as mock_MQTTThread:
                                mock_restx.get_site_dict.return_value = site_config
                                mock_manager.get_manager_dict_from_config.return_value = manager_dict

                                SUT = MQTTPublish(mock_StdEngine, config)

                                mock_MQTTThread.assert_called_once_with('MQTTPublish', SUT.archive_queue, **site_config_final)

if __name__ == '__main__':
    test_suite = unittest.TestSuite()
    test_suite.addTest(TestInitialization('test_topicsunit_system'))
    unittest.TextTestRunner().run(test_suite)

    #unittest.main(exit=False)
