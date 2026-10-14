import gzip
from functools import partial

import pytest

from parfive import Downloader
from parfive.tests.localserver import BaseTestServer, error_on_nth_get_request
from parfive.utils import MultiPartDownloadError


def test_multipart(multipartserver, tmp_path):
    dl = Downloader(progress=False)
    max_splits = 5
    dl.enqueue_file(multipartserver.url, path=tmp_path, max_splits=max_splits)
    files = dl.download()

    # Verify we transferred all the content
    with open(files[0], "rb") as fobj:
        assert fobj.read() == b"a" * 100

    # Assert that we made the expected number of requests
    assert len(multipartserver.requests) == max_splits + 1
    assert "HTTP_RANGE" not in multipartserver.requests[0]
    for split_req in multipartserver.requests[1:]:
        assert "HTTP_RANGE" in split_req


def test_multipart_with_error(multipartserver, tmp_path):
    multipartserver.callback = partial(error_on_nth_get_request, 3)
    dl = Downloader(progress=False)
    max_splits = 5
    dl.enqueue_file(multipartserver.url, path=tmp_path, max_splits=max_splits)
    files = dl.download()

    assert len(files) == 0
    assert len(files.errors) == 1
    assert isinstance(files.errors[0].exception, MultiPartDownloadError)

    expected_file = tmp_path / "testfile.txt"
    assert not expected_file.exists()


class GzipTestServer(BaseTestServer):
    """
    Serves gzip-encoded content, and ranges of the encoded bytes.
    """

    content = gzip.compress(b"a" * 100)

    def default_request_handler(self, environ, start_response):
        body = self.content
        if http_range := environ.get("HTTP_RANGE"):
            start, end = http_range.split("bytes=")[1].split("-")
            body = body[int(start) : int(end) if end else None]
        start_response(
            "200 OK",
            [
                ("Content-Encoding", "gzip"),
                ("Content-Length", str(len(body))),
                ("Accept-Ranges", "bytes"),
                ("Content-Disposition", "attachment; filename=testfile.txt"),
            ],
        )
        return [body]


@pytest.fixture
def gzipserver():
    server = GzipTestServer()
    server.start_server()
    yield server
    server.stop_server()


def test_multipart_content_encoding(gzipserver, tmp_path):
    # Ranges of an encoded response can not be decoded on their own (#121)
    dl = Downloader(progress=False)
    dl.enqueue_file(gzipserver.url, path=tmp_path, max_splits=5)
    files = dl.download()

    assert not files.errors
    with open(files[0], "rb") as fobj:
        assert fobj.read() == b"a" * 100
    assert gzipserver.requests_by_method["GET"] == 1
