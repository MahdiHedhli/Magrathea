"""Offline notification configuration tests; no requests leave this process."""
import importlib
import os
import unittest
from unittest.mock import patch
from conductor import config, ntfy

class NotificationConfigurationTests(unittest.TestCase):
    def test_no_default_topic(self):
        with patch.dict(os.environ, {}, clear=True):
            importlib.reload(config)
            self.assertEqual(config.NTFY_TOPIC, "")
        importlib.reload(config)

    def test_explicit_topic_is_preserved(self):
        with patch.dict(os.environ, {"CONDUCTOR_NTFY_TOPIC": "operator-supplied"}):
            importlib.reload(config)
            self.assertEqual(config.NTFY_TOPIC, "operator-supplied")
        importlib.reload(config)

    def test_missing_topic_prevents_network(self):
        with patch.object(config, "NTFY_TOPIC", ""), patch("urllib.request.urlopen") as network:
            self.assertFalse(ntfy.progress("test", "test"))
            network.assert_not_called()

    def test_whitespace_topic_prevents_network(self):
        with patch.object(config, "NTFY_TOPIC", " "), patch("urllib.request.urlopen") as network:
            self.assertFalse(ntfy.blocker("test", "test"))
            network.assert_not_called()

if __name__ == "__main__":
    unittest.main()
