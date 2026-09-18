from app.extract.fetch import FetchError, assert_public_http_url
import pytest


def test_rejects_file_scheme():
    with pytest.raises(FetchError):
        assert_public_http_url("file:///etc/passwd")


def test_rejects_localhost():
    with pytest.raises(FetchError):
        assert_public_http_url("http://localhost:8000/secret")


def test_rejects_loopback_ip():
    with pytest.raises(FetchError):
        assert_public_http_url("http://127.0.0.1/x")
