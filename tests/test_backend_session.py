import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'custom_components', 'aarlo'))

from unittest.mock import MagicMock, patch
from pyaarlo.core.backend import ArloBackEnd, _AuthDetails


def _make_cfg(http_backend="curl_cffi", impersonate="chrome131"):
    cfg = MagicMock()
    cfg.http_backend = http_backend
    cfg.curl_cffi_impersonate = impersonate
    cfg.user_agent = "arlo"
    cfg.ecdh_curves = ["secp384r1"]
    return cfg


def test_curl_cffi_session_created_when_backend_is_curl_cffi():
    cfg = _make_cfg(http_backend="curl_cffi", impersonate="chrome110")
    backend = ArloBackEnd.__new__(ArloBackEnd)
    backend._cfg = cfg
    backend._log = MagicMock()
    backend._auth = _AuthDetails()
    backend._req = MagicMock()
    backend._req.details = MagicMock()
    backend._req.details.cookies = None

    mock_session = MagicMock()
    mock_async_session = MagicMock()
    mock_cffi_requests = MagicMock()
    mock_cffi_requests.Session.return_value = mock_session
    mock_cffi_requests.AsyncSession.return_value = mock_async_session

    mock_curl_cffi = MagicMock()
    mock_curl_cffi.requests = mock_cffi_requests

    with patch.dict("sys.modules", {"curl_cffi": mock_curl_cffi, "curl_cffi.requests": mock_cffi_requests}):
        assert backend._auth_get_connection() is True

    mock_cffi_requests.Session.assert_called_once_with(impersonate="chrome110")
    mock_cffi_requests.AsyncSession.assert_called_once_with(impersonate="chrome110")
    assert backend._req.details.connection is mock_session
    assert backend._req.details.async_connection is mock_async_session


def test_cloudscraper_session_created_when_backend_is_cloudscraper():
    cfg = _make_cfg(http_backend="cloudscraper")
    backend = ArloBackEnd.__new__(ArloBackEnd)
    backend._cfg = cfg
    backend._log = MagicMock()
    backend._auth = _AuthDetails()
    backend._auth.curves = ["secp384r1"]
    backend._req = MagicMock()
    backend._req.details = MagicMock()
    backend._req.details.cookies = None

    mock_session = MagicMock()
    mock_cloudscraper = MagicMock()
    mock_cloudscraper.create_scraper.return_value = mock_session

    with patch.dict("sys.modules", {"cloudscraper": mock_cloudscraper}):
        assert backend._auth_get_connection() is True

    mock_cloudscraper.create_scraper.assert_called_once_with(
        disableCloudflareV1=True,
        ecdhCurve="secp384r1",
        debug=False,
    )
    assert backend._req.details.connection is mock_session
