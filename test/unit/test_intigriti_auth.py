"""Unit tests for intigriti_auth.main()'s control flow.

OAuth2Client and the browser leg (get_redirect_via_browser) are mocked out here --
no real network or browser calls are made. See test/int for tests that exercise
the real Playwright browser automation.
"""

import unittest
from unittest.mock import MagicMock, patch

import intigriti_auth


class TestConstants(unittest.TestCase):
    def test_default_scopes_matches_joined_string(self):
        self.assertEqual(intigriti_auth.DEFAULT_SCOPES, ','.join(intigriti_auth.default_scopes))

    def test_browser_channels_maps_expected_keys(self):
        self.assertEqual(
            intigriti_auth.BROWSER_CHANNELS,
            {'chromium': None, 'chrome': 'chrome', 'msedge': 'msedge'},
        )


class MainTestCase(unittest.TestCase):
    """Base class wiring up a mocked OAuth2Client session for main() tests."""

    def _mock_session(self, mock_oauth2client_cls, fetch_token_return=None, refresh_token_return=None):
        session = MagicMock()
        session.create_authorization_url.return_value = (
            'https://login.intigriti.com/connect/authorize?...', 'state123',
        )
        session.fetch_token.return_value = fetch_token_return if fetch_token_return is not None else {
            'access_token': 'AT1', 'refresh_token': 'RT1',
        }
        session.refresh_token.return_value = refresh_token_return if refresh_token_return is not None else {
            'refresh_token': 'RT2',
        }
        mock_oauth2client_cls.return_value = session
        return session


class TestScopeHandling(MainTestCase):
    @patch('intigriti_auth.OAuth2Client')
    @patch('builtins.input', return_value='https://localhost/?code=abc&state=state123')
    def test_falls_back_to_default_scopes_when_scopes_empty(self, mock_input, mock_oauth2client_cls):
        self._mock_session(mock_oauth2client_cls)
        intigriti_auth.main(client_id='id', client_secret='secret', scopes='', manual=True)
        self.assertEqual(mock_oauth2client_cls.call_args.kwargs['scope'], intigriti_auth.default_scopes)

    @patch('intigriti_auth.OAuth2Client')
    @patch('builtins.input', return_value='https://localhost/?code=abc&state=state123')
    def test_splits_comma_separated_scopes(self, mock_input, mock_oauth2client_cls):
        self._mock_session(mock_oauth2client_cls)
        intigriti_auth.main(client_id='id', client_secret='secret', scopes='a,b,c', manual=True)
        self.assertEqual(mock_oauth2client_cls.call_args.kwargs['scope'], ['a', 'b', 'c'])


class TestBrowserFlowSelection(MainTestCase):
    @patch('intigriti_auth.OAuth2Client')
    @patch('builtins.input', return_value='https://localhost/?code=abc&state=state123')
    def test_manual_flow_prompts_for_input_and_skips_browser(self, mock_input, mock_oauth2client_cls):
        self._mock_session(mock_oauth2client_cls)
        with patch('intigriti_auth.get_redirect_via_browser') as mock_get_redirect:
            intigriti_auth.main(client_id='id', client_secret='secret', manual=True)
        mock_input.assert_called_once()
        mock_get_redirect.assert_not_called()

    @patch('intigriti_auth.OAuth2Client')
    def test_auto_flow_drives_browser_with_selected_channel(self, mock_oauth2client_cls):
        self._mock_session(mock_oauth2client_cls)
        fake_redirect = 'https://localhost/?code=abc&state=x'
        with patch('intigriti_auth.get_redirect_via_browser', return_value=fake_redirect) as mock_get_redirect:
            intigriti_auth.main(client_id='id', client_secret='secret', manual=False, browser='msedge')
        mock_get_redirect.assert_called_once()
        self.assertEqual(mock_get_redirect.call_args.kwargs['channel'], 'msedge')


class TestUatEnvironment(MainTestCase):
    @patch('intigriti_auth.OAuth2Client')
    @patch('builtins.input', return_value='https://localhost/?code=abc&state=state123')
    def test_uat_true_targets_uat_subdomain(self, mock_input, mock_oauth2client_cls):
        session = self._mock_session(mock_oauth2client_cls)
        intigriti_auth.main(client_id='id', client_secret='secret', manual=True, uat=True)
        auth_url_kwarg = session.create_authorization_url.call_args.kwargs['url']
        self.assertIn('login-uat.intigriti.com', auth_url_kwarg)

    @patch('intigriti_auth.OAuth2Client')
    @patch('builtins.input', return_value='https://localhost/?code=abc&state=state123')
    def test_uat_false_targets_production_subdomain(self, mock_input, mock_oauth2client_cls):
        session = self._mock_session(mock_oauth2client_cls)
        intigriti_auth.main(client_id='id', client_secret='secret', manual=True, uat=False)
        auth_url_kwarg = session.create_authorization_url.call_args.kwargs['url']
        self.assertIn('login.intigriti.com', auth_url_kwarg)
        self.assertNotIn('login-uat.intigriti.com', auth_url_kwarg)


class TestRefreshTokenHandling(MainTestCase):
    @patch('intigriti_auth.OAuth2Client')
    @patch('builtins.input', return_value='https://localhost/?code=abc&state=state123')
    def test_scope_is_cleared_before_refresh_call(self, mock_input, mock_oauth2client_cls):
        """Regression guard: Intigriti returns a 400 if scope is included on the
        refresh_token call, so main() must clear session.scope before calling it."""
        session = self._mock_session(mock_oauth2client_cls)
        scope_at_refresh_time = {}

        def _refresh_side_effect(**kwargs):
            scope_at_refresh_time['value'] = session.scope
            return {'refresh_token': 'RT2'}

        session.refresh_token.side_effect = _refresh_side_effect
        intigriti_auth.main(client_id='id', client_secret='secret', manual=True)
        self.assertIsNone(scope_at_refresh_time['value'])

    @patch('intigriti_auth.OAuth2Client')
    @patch('builtins.input', return_value='https://localhost/?code=abc&state=state123')
    def test_returns_token_resp_when_truthy(self, mock_input, mock_oauth2client_cls):
        self._mock_session(
            mock_oauth2client_cls,
            fetch_token_return={'access_token': 'AT1', 'refresh_token': 'RT1'},
        )
        result = intigriti_auth.main(client_id='id', client_secret='secret', manual=True)
        self.assertEqual(result, {'access_token': 'AT1', 'refresh_token': 'RT1'})

    @patch('intigriti_auth.OAuth2Client')
    @patch('builtins.input', return_value='https://localhost/?code=abc&state=state123')
    def test_returns_refresh_token_when_fetch_token_falsy(self, mock_input, mock_oauth2client_cls):
        self._mock_session(
            mock_oauth2client_cls,
            fetch_token_return={},
            refresh_token_return={'refresh_token': 'RT2'},
        )
        result = intigriti_auth.main(client_id='id', client_secret='secret', manual=True)
        self.assertEqual(result, 'RT2')


if __name__ == '__main__':
    unittest.main()
