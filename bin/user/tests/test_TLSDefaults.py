# pylint: disable=missing-docstring, invalid-name, line-too-long, dangerous-default-value
import ssl

import unittest

from user.mqtt import TLSDefaults

class TestTLSDefaults(unittest.TestCase):
    def test_PROTOCOL_TLS(self):
        tls_version = 'tls'

        try:
            saved_version = ssl.PROTOCOL_TLS
            del ssl.PROTOCOL_TLS
        except AttributeError:
            saved_version = None

        SUT = TLSDefaults()
        self.assertNotIn(tls_version, SUT.TLS_VER_OPTIONS)

        if saved_version:
            ssl.PROTOCOL_TLS = saved_version
            SUT = TLSDefaults()
            self.assertIn(tls_version, SUT.TLS_VER_OPTIONS)

    def test_PROTOCOL_TLSv1(self):
        tls_version = 'tlsv1'

        try:
            saved_version = ssl.PROTOCOL_TLSv1
            del ssl.PROTOCOL_TLSv1
        except AttributeError:
            saved_version = None

        SUT = TLSDefaults()
        self.assertNotIn(tls_version, SUT.TLS_VER_OPTIONS)

        if saved_version:
            ssl.PROTOCOL_TLSv1 = saved_version
            SUT = TLSDefaults()
            self.assertIn(tls_version, SUT.TLS_VER_OPTIONS)

    def test_PROTOCOL_TLSv1_1(self):
        tls_version = 'tlsv11'

        try:
            saved_version = ssl.PROTOCOL_TLSv1_1
            del ssl.PROTOCOL_TLSv1_1
        except AttributeError:
            saved_version = None

        SUT = TLSDefaults()
        self.assertNotIn(tls_version, SUT.TLS_VER_OPTIONS)

        if saved_version:
            ssl.PROTOCOL_TLSv1_1 = saved_version
            SUT = TLSDefaults()
            self.assertIn(tls_version, SUT.TLS_VER_OPTIONS)

    def test_PROTOCOL_TLSv1_2(self):
        tls_version = 'tlsv12'

        try:
            saved_version = ssl.PROTOCOL_TLSv1_2
            del ssl.PROTOCOL_TLSv1_2
        except AttributeError:
            saved_version = None

        SUT = TLSDefaults()
        self.assertNotIn(tls_version, SUT.TLS_VER_OPTIONS)

        if saved_version:
            ssl.PROTOCOL_TLSv1_2 = saved_version
            SUT = TLSDefaults()
            self.assertIn(tls_version, SUT.TLS_VER_OPTIONS)

    def test_PROTOCOL_SSLv2(self):
        tls_version = 'sslv2'

        try:
            saved_version = ssl.PROTOCOL_SSLv2
            del ssl.PROTOCOL_SSLv2
        except AttributeError:
            saved_version = None

        SUT = TLSDefaults()
        self.assertNotIn(tls_version, SUT.TLS_VER_OPTIONS)

        if saved_version:
            ssl.PROTOCOL_SSLv2 = saved_version
            SUT = TLSDefaults()
            self.assertIn(tls_version, SUT.TLS_VER_OPTIONS)

    def test_missing_PROTOCOL_SSLv23(self):
        tls_version = 'sslv23'

        try:
            saved_version = ssl.PROTOCOL_SSLv23
            del ssl.PROTOCOL_SSLv23
        except AttributeError:
            saved_version = None

        SUT = TLSDefaults()
        self.assertNotIn(tls_version, SUT.TLS_VER_OPTIONS)

        if saved_version:
            ssl.PROTOCOL_SSLv23 = saved_version
            SUT = TLSDefaults()
            self.assertIn(tls_version, SUT.TLS_VER_OPTIONS)

    def test_missing_PROTOCOL_SSLv3(self):
        tls_version = 'sslv3'

        try:
            saved_version = ssl.PROTOCOL_SSLv3
            del ssl.PROTOCOL_SSLv3
        except AttributeError:
            saved_version = None

        SUT = TLSDefaults()
        self.assertNotIn(tls_version, SUT.TLS_VER_OPTIONS)

        if saved_version:
            ssl.PROTOCOL_SSLv3 = saved_version
            SUT = TLSDefaults()
            self.assertIn(tls_version, SUT.TLS_VER_OPTIONS)


if __name__ == '__main__':
    #test_suite = unittest.TestSuite()
    #test_suite.addTest(TestTLSDefaults('test_new'))
    #unittest.TextTestRunner().run(test_suite)

    unittest.main(exit=False)
