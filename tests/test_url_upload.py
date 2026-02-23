import urllib.parse


class TestUrlSchemeValidation:
    def test_http_allowed(self):
        assert urllib.parse.urlparse("http://example.com").scheme in ("http", "https")

    def test_https_allowed(self):
        assert urllib.parse.urlparse("https://example.com").scheme in ("http", "https")

    def test_ftp_rejected(self):
        assert urllib.parse.urlparse("ftp://example.com").scheme not in ("http", "https")

    def test_file_rejected(self):
        assert urllib.parse.urlparse("file:///etc/passwd").scheme not in ("http", "https")

    def test_file_path_traversal_rejected(self):
        assert urllib.parse.urlparse("file:///../../etc/passwd").scheme not in ("http", "https")

    def test_no_scheme_rejected(self):
        assert urllib.parse.urlparse("/etc/passwd").scheme not in ("http", "https")

    def test_relative_path_rejected(self):
        assert urllib.parse.urlparse("../../etc/passwd").scheme not in ("http", "https")
