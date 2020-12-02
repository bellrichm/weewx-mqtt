# pylint: disable=missing-docstring, invalid-name, line-too-long, dangerous-default-value
import random
import ssl
import string

import unittest

import configobj

from user.mqtt import MQTTThread

def random_string():
    return ''.join([random.choice(string.ascii_letters + string.digits) for n in range(32)])

class TestTLSInitialization(unittest.TestCase):
    @staticmethod
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

    def test_certs_required(self):
        site_dict = {
            'server_url' : random_string,
            'topics': {
                'weather/loop': self.create_topic(),
                'weather': self.create_topic(aggregation='individual')
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
                'weather/loop': self.create_topic(),
                'weather': self.create_topic(aggregation='individual')
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
                'weather/loop': self.create_topic(),
                'weather': self.create_topic(aggregation='individual')
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

if __name__ == '__main__':
    #test_suite = unittest.TestSuite()
    #test_suite.addTest(TestTLSInitialization('test_new'))
    #unittest.TextTestRunner().run(test_suite)

    unittest.main(exit=False)
