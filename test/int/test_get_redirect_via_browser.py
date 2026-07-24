"""Integration tests for get_redirect_via_browser().

These launch a real (headed) Chromium browser via Playwright against a local
HTTP fixture server -- slower and heavier than test/unit, and require
`playwright install chromium` to have been run first.
"""

import http.server
import tempfile
import threading
import unittest
from pathlib import Path

import intigriti_auth

CALLBACK = 'https://localhost/'

REDIRECT_FIXTURE = f"""<html><body>
<script>
setTimeout(function() {{
  window.location = '{CALLBACK}?code=abc123&state=xyz789';
}}, 500);
</script>
</body></html>"""

NO_REDIRECT_FIXTURE = '<html><body>no redirect happens on this page</body></html>'


class _FixtureServer:
    """Serves static HTML fixtures on an OS-assigned local port for a test."""

    def __init__(self, directory: str):
        def handler(*args, **kwargs):
            return http.server.SimpleHTTPRequestHandler(*args, directory=directory, **kwargs)

        self.httpd = http.server.HTTPServer(('127.0.0.1', 0), handler)
        self.port = self.httpd.server_port
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=5)


class TestGetRedirectViaBrowser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.TemporaryDirectory()
        (Path(cls.tmpdir.name) / 'redirect.html').write_text(REDIRECT_FIXTURE)
        (Path(cls.tmpdir.name) / 'no_redirect.html').write_text(NO_REDIRECT_FIXTURE)
        cls.server = _FixtureServer(cls.tmpdir.name)
        cls.server.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()
        cls.tmpdir.cleanup()

    def test_captures_redirect_url_without_connecting_to_it(self):
        url = f'http://127.0.0.1:{self.server.port}/redirect.html'
        result = intigriti_auth.get_redirect_via_browser(url, CALLBACK, timeout_s=15)
        self.assertEqual(result, f'{CALLBACK}?code=abc123&state=xyz789')

    def test_raises_timeout_error_when_no_redirect_occurs(self):
        url = f'http://127.0.0.1:{self.server.port}/no_redirect.html'
        with self.assertRaises(TimeoutError):
            intigriti_auth.get_redirect_via_browser(url, CALLBACK, timeout_s=2)


if __name__ == '__main__':
    unittest.main()
