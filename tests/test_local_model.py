"""HTTP contract tests with a stub reviewer; these do not test model quality."""
import importlib.util
import json
from pathlib import Path
import threading
import unittest
from urllib.request import Request, urlopen
from urllib.error import HTTPError

spec = importlib.util.spec_from_file_location('local_model', Path(__file__).resolve().parents[1] / 'backend/local_model.py')
service = importlib.util.module_from_spec(spec)
spec.loader.exec_module(service)


class FakeReviewer:
    def __init__(self):
        self.sources = []

    def review(self, source):
        self.sources.append(source)
        return {'state': 'completed', 'output': '{}', 'seconds': 0}


class ServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reviewer = FakeReviewer()
        cls.server = service.Server(('127.0.0.1', 0), cls.reviewer)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def request(self, path, value=None, headers=None):
        request = Request(self.url + path, data=json.dumps(value).encode() if value is not None else None,
                          headers={'Content-Type': 'application/json', **(headers or {})})
        try:
            with urlopen(request, timeout=3) as response:
                return response.status, json.load(response)
        except HTTPError as error:
            return error.code, json.load(error)

    def test_health(self):
        status, value = self.request('/health')
        self.assertEqual(status, 200)
        self.assertEqual(value['profileId'], 'aes128-gcm-tampering-v1')
        self.assertIsNone(value['adapter'])

    def test_source_is_data_and_other_profiles_are_rejected(self):
        source = 'untrusted code\r\nreturn true;'
        status, _ = self.request('/review', {'source': source, 'profileId': service.PROFILE['id']})
        self.assertEqual(status, 200)
        self.assertEqual(self.reviewer.sources[-1], source.replace('\r\n', '\n'))
        self.assertEqual(self.request('/review', {'source': source, 'profileId': 'ckks'})[0], 400)
        self.assertEqual(self.request('/review', {'source': source, 'profileId': service.PROFILE['id'], 'url': 'https://example.com'})[0], 400)
        self.assertEqual(self.request('/review', {'source': '\0', 'profileId': service.PROFILE['id']})[0], 400)

    def test_unknown_routes_origins_and_busy_requests(self):
        self.assertEqual(self.request('/train', {})[0], 404)
        self.assertEqual(self.request('/health', headers={'Origin': 'http://evil.example'})[0], 403)
        with self.server.review_lock:
            self.assertEqual(self.request('/health')[1]['state'], 'busy')
            self.assertEqual(self.request('/review', {'source': 'code', 'profileId': service.PROFILE['id']})[0], 429)

    def test_loading_and_failed_model_remain_observable(self):
        try:
            for state in ('loading', 'error'):
                self.server.state = state
                self.assertEqual(self.request('/health')[1]['state'], state)
                self.assertEqual(self.request('/review', {'source': 'code', 'profileId': service.PROFILE['id']})[0], 503)
        finally:
            self.server.state = 'ready'


if __name__ == '__main__':
    unittest.main()
