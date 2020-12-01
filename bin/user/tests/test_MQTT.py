# pylint: disable=missing-docstring, invalid-name
import unittest
import mock
from user.mqtt import MQTT

class TestInitialization(unittest.TestCase):
    def test_topic_set(self):
        mock_StdEngine = mock.Mock()
        config_dict = {}
        SUT = MQTT(mock_StdEngine, config_dict)
        self.assertTrue(True)
        print("done")

if __name__ == '__main__':
    test_suite = unittest.TestSuite()
    test_suite.addTest(TestInitialization('test_topic_set'))
    unittest.TextTestRunner().run(test_suite)

    #unittest.main(exit=False)
