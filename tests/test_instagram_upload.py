from src.previsao.publish import instagram


def test_sends_mp4_bytes_to_meta(tmp_path, monkeypatch):
    path = tmp_path / "reel.mp4"
    path.write_bytes(b"video")
    monkeypatch.setattr(instagram, "_cfg", lambda: ("123", "test-token", "v26.0", "previsaopr"))
    sent = []

    class Reply:
        status_code = 200

        def __init__(self, payload):
            self.payload = payload

        def json(self):
            return self.payload

    def post(url, **kwargs):
        sent.append(url)
        if len(sent) == 1:
            assert kwargs["data"]["upload_type"] == "resumable"
            assert "video_url" not in kwargs["data"]
            return Reply({"id": "456"})
        assert kwargs["headers"]["file_size"] == "5"
        assert kwargs["data"].read() == b"video"
        return Reply({"success": True})

    monkeypatch.setattr(instagram, "_post", post)
    assert instagram.create_reel(None, "Previsão", video_file=path) == "456"
    assert sent == [
        "https://graph.facebook.com/v26.0/123/media",
        "https://rupload.facebook.com/ig-api-upload/v26.0/456",
    ]
