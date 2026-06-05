import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'custom_components', 'aarlo'))

from unittest.mock import MagicMock
from pyaarlo.cfg import ArloCfg


def _cfg(**kwargs):
    return ArloCfg(MagicMock(), **kwargs)


def test_http_backend_default():
    assert _cfg().http_backend == "curl_cffi"


def test_http_backend_cloudscraper():
    assert _cfg(http_backend="cloudscraper").http_backend == "cloudscraper"


def test_curl_cffi_impersonate_default():
    assert _cfg().curl_cffi_impersonate == "chrome131"


def test_curl_cffi_impersonate_custom():
    assert _cfg(curl_cffi_impersonate="safari17_0").curl_cffi_impersonate == "safari17_0"
