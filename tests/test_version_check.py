import http.server
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest
import urllib.parse


SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'resolve_versions.py'
IMAGE = 'ghcr.io/lizhian/caddy-lizhian'


class API(http.server.BaseHTTPRequestHandler):
    requests = []
    version = 'v2.11.7'
    prerelease = False

    def do_GET(self):
        path = urllib.parse.urlsplit(self.path).path
        type(self).requests.append(path)
        if path == '/repos/caddyserver/caddy/releases/latest':
            value = {'tag_name': self.version, 'draft': False, 'prerelease': self.prerelease}
        elif path.endswith('/commits'):
            value = [{'sha': 'a' * 40}]
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(value).encode())

    def log_message(self, *_):
        pass


class VersionCheck(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), API)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def setUp(self):
        API.requests = []
        API.version = 'v2.11.7'
        API.prerelease = False
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.previous = self.directory / 'previous.json'
        self.previous.write_text(json.dumps({'caddy_version': 'v2.11.7', 'image': IMAGE}))

    def check(self, *extra, success=True):
        original = self.previous.read_bytes() if self.previous.exists() else None
        env = {k: v for k, v in os.environ.items() if k not in ('GH_TOKEN', 'GITHUB_TOKEN')}
        env['GITHUB_API_URL'] = f'http://127.0.0.1:{self.server.server_port}'
        env['GITHUB_STEP_SUMMARY'] = str(self.directory / 'summary.md')
        result = subprocess.run([
            'python3', str(SCRIPT), '--previous', str(self.previous), '--image', IMAGE,
            '--output', str(self.directory / 'versions.json'),
            '--github-output', str(self.directory / 'github-output'), *extra,
        ], text=True, capture_output=True, env=env)
        self.assertEqual(result.returncode == 0, success, result.stderr)
        self.assertEqual(self.previous.read_bytes() if self.previous.exists() else None, original)
        if not success:
            return
        values = dict(line.split('=', 1) for line in (self.directory / 'github-output').read_text().splitlines())
        return json.loads(result.stdout), values

    def test_unchanged_skips_build_and_plugin_requests(self):
        result, output = self.check()
        self.assertFalse(result['should_build'])
        self.assertEqual(output['should_build'], 'false')
        self.assertEqual(API.requests, ['/repos/caddyserver/caddy/releases/latest'])
        self.assertFalse((self.directory / 'versions.json').exists())

    def test_caddy_change_resolves_all_plugins(self):
        API.version = 'v2.11.8'
        result, output = self.check()
        self.assertTrue(result['should_build'])
        self.assertEqual(output['reason'], 'caddy_version_changed')
        self.assertEqual(output['caddy_version'], 'v2.11.8')
        self.assertCountEqual(API.requests, [
            '/repos/caddyserver/caddy/releases/latest',
            '/repos/caddyserver/forwardproxy/commits',
            '/repos/mholt/caddy-l4/commits',
            '/repos/caddy-dns/cloudflare/commits',
        ])

    def test_missing_publication_builds_once(self):
        self.previous.unlink()
        result, _ = self.check()
        self.assertTrue(result['should_build'])
        self.assertEqual(result['reason'], 'first_publication')

    def test_image_rename_requires_first_publication(self):
        self.previous.write_text(json.dumps({'caddy_version': 'v2.11.7', 'image': 'ghcr.io/lizhian/previous-image'}))
        result, _ = self.check()
        self.assertTrue(result['should_build'])
        self.assertEqual(result['reason'], 'first_publication')

    def test_manual_force_fetches_updated_plugins(self):
        result, output = self.check('--force')
        self.assertTrue(result['should_build'])
        self.assertEqual(output['reason'], 'forced')
        self.assertEqual(len(API.requests), 4)

    def test_failed_publication_remains_eligible_for_retry(self):
        API.version = 'v2.11.8'
        first, _ = self.check()
        second, _ = self.check()
        self.assertTrue(first['should_build'] and second['should_build'])

    def test_prerelease_is_rejected(self):
        API.version = 'v2.12.0-rc.1'
        API.prerelease = True
        self.check(success=False)
        self.assertEqual(len(API.requests), 1)


if __name__ == '__main__':
    unittest.main()
