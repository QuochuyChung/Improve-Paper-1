"""Đối tượng giả cho test drift_check: API serving, Pushgateway và GitHub."""

import requests

SERVING = "http://serving.test:8000"
PUSHGATEWAY = "http://pushgateway.test:9091"
GITHUB = "https://api.github.com/repos/owner/repo/issues"
FEATURES = ["f0", "f1", "f2", "f3", "f4", "f5"]
REF = {f: {"mean": 10.0 * (i + 1), "std": 2.0} for i, f in enumerate(FEATURES)}


class FakeResponse:
    def __init__(self, status=200, body=None):
        self.status_code, self._body = status, body

    def json(self):
        return self._body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} lỗi giả")


class FakeSession:
    """Thay requests.Session: API serving, Pushgateway và GitHub đều là đối tượng giả."""

    def __init__(self, model=None, stats=None, open_issues=None, created_number=7):
        self.model = model if model is not None else {"run_id": "baseline-001"}
        self.stats = stats
        self.open_issues = open_issues if open_issues is not None else []
        self.created_number = created_number
        self.serving_error = None
        self.list_status = 200
        self.create_status = 201
        self.push_status = 200
        self.posts, self.puts, self.gets = [], [], []

    def get(self, url, params=None, headers=None, timeout=None):
        self.gets.append(url)
        if url.startswith(SERVING):
            if self.serving_error:
                raise self.serving_error
            return FakeResponse(200, self.model if url.endswith("/model") else self.stats)
        assert url == GITHUB, url
        return FakeResponse(self.list_status, self.open_issues)

    def post(self, url, json=None, headers=None, timeout=None):
        assert url == GITHUB, url
        self.posts.append(json)
        return FakeResponse(self.create_status, {"number": self.created_number})

    def put(self, url, data=None, timeout=None):
        self.puts.append((url, data))
        return FakeResponse(self.push_status, {})


def make_stats(n, shift_per_feature):
    """Thống kê dạng /stats, mean dịch shift std tham chiếu theo từng feature."""
    return {
        "n": n,
        "features": {
            f: {"mean": REF[f]["mean"] + shift_per_feature.get(f, 0.0) * REF[f]["std"], "std": 2.0}
            for f in FEATURES
        },
    }
