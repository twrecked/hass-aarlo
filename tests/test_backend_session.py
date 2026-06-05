import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'custom_components', 'aarlo'))

from unittest.mock import MagicMock, patch


def _make_arlo(http_backend="curl_cffi", impersonate="chrome131"):
    """Minimal fake arlo object for testing session creation."""
    cfg = MagicMock()
    cfg.http_backend = http_backend
    cfg.curl_cffi_impersonate = impersonate
    cfg.user_agent = "arlo"
    cfg.ecdh_curves = ["secp384r1"]
    arlo = MagicMock()
    arlo.cfg = cfg
    return arlo


def test_curl_cffi_session_created_when_backend_is_curl_cffi():
    from pyaarlo.backend import ArloBackEnd

    arlo = _make_arlo(http_backend="curl_cffi", impersonate="chrome110")
    backend = ArloBackEnd.__new__(ArloBackEnd)
    backend._arlo = arlo
    backend._cookies = None

    mock_session = MagicMock()
    mock_cffi_requests = MagicMock()
    mock_cffi_requests.Session.return_value = mock_session

    mock_curl_cffi = MagicMock()
    mock_curl_cffi.requests = mock_cffi_requests

    with patch.dict("sys.modules", {"curl_cffi": mock_curl_cffi, "curl_cffi.requests": mock_cffi_requests}):
        backend._create_session()

    mock_cffi_requests.Session.assert_called_once_with(impersonate="chrome110")
    assert backend._session is mock_session


def test_cloudscraper_session_created_when_backend_is_cloudscraper():
    from pyaarlo.backend import ArloBackEnd

    arlo = _make_arlo(http_backend="cloudscraper")
    backend = ArloBackEnd.__new__(ArloBackEnd)
    backend._arlo = arlo
    backend._cookies = None

    mock_session = MagicMock()
    mock_cloudscraper = MagicMock()
    mock_cloudscraper.create_scraper.return_value = mock_session

    with patch.dict("sys.modules", {"cloudscraper": mock_cloudscraper}):
        backend._create_session(curve="secp384r1")

    mock_cloudscraper.create_scraper.assert_called_once_with(
        disableCloudflareV1=True,
        ecdhCurve="secp384r1",
        debug=False,
    )
    assert backend._session is mock_session
