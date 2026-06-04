import unittest
import urllib.error
from unittest.mock import patch

import add_to_anki


class AnkiRequestTests(unittest.TestCase):
    def test_reports_missing_ankiconnect_with_setup_hint(self):
        error = urllib.error.URLError(ConnectionRefusedError(10061, "connection refused"))

        with patch("add_to_anki.urllib.request.urlopen", side_effect=error):
            with self.assertRaisesRegex(Exception, "AnkiConnect.*2055492159"):
                add_to_anki.anki_request("version")


if __name__ == "__main__":
    unittest.main()
