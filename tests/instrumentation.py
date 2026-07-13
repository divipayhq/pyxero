from __future__ import unicode_literals

import unittest
from mock import Mock

from xero.instrumentation import last_response_size, record_response_size


class InstrumentationTest(unittest.TestCase):
    def setUp(self):
        last_response_size.set(None)

    def test_records_content_length_and_body(self):
        response = Mock()
        response.headers = {"Content-Length": "1234"}
        response.content = b"short"

        record_response_size(response)

        self.assertEqual(
            last_response_size.get(),
            {"content_length": 1234, "body_bytes": 5},
        )

    def test_records_body_when_no_content_length(self):
        response = Mock()
        response.headers = {}
        response.content = b"abcd"

        record_response_size(response)

        self.assertEqual(
            last_response_size.get(),
            {"content_length": None, "body_bytes": 4},
        )

    def test_never_raises_on_bad_response(self):
        response = Mock()
        response.headers = {"Content-Length": "not-an-int"}

        record_response_size(response)

        self.assertIsNone(last_response_size.get())
