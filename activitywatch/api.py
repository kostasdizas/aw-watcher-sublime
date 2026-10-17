import socket
import requests
from datetime import datetime, timezone
from typing import Any, Dict

from . import utils


class TimeoutSession(requests.Session):
    """A session that always sends a timeout."""

    def __init__(self, timeout: int) -> None:
        super().__init__()
        self._timeout = timeout

    def request(self, *args: Any, **kwargs: Any) -> requests.Response:
        kwargs.setdefault("timeout", self._timeout)
        return super().request(*args, **kwargs)


class ActivityWatchApi(object):

    _api_timeout = 5

    def __init__(self) -> None:
        utils.log("ActivityWatchApi initializing")
        self.debug = False
        self._last_heartbeat = datetime.min.replace(tzinfo=timezone.utc)
        self._session = TimeoutSession(self._api_timeout)

    def setup(self, client_name: str, host: str, port: int, min_seconds: int) -> None:
        self.url = "http://{}:{}".format(host, port)
        self.client_name = client_name
        self.hostname = socket.gethostname()
        self.min_seconds = min_seconds

    def enable_debugging(self) -> None:
        self.debug = True
        utils.log("API debugging enabled")

    def disable_debugging(self) -> None:
        if self.debug:
            utils.log("API debugging disabled")
        self.debug = False

    def _make_url(self, endpoint: str) -> str:
        return "{}/api/0/{}".format(self.url, endpoint)

    def _rate_limited(self, now: datetime) -> bool:
        return (now - self._last_heartbeat).total_seconds() > self.min_seconds

    def check(self) -> bool:
        if self.debug:
            utils.log("Checking server connection")
        try:
            resp = self._session.get(self._make_url("info"))
        except requests.RequestException as err:
            if self.debug:
                utils.log("could not connect: {}".format(err))
            return False
        return resp.status_code == 200

    def get_bucket(self, bucket_id: str) -> Any:
        if self.debug:
            utils.log("Retrieving bucket")
        endpoint = "buckets/{}".format(bucket_id)
        resp = self._session.get(self._make_url(endpoint))
        return resp.json()

    def create_bucket(self, bucket_id: str) -> Any:
        if self.debug:
            utils.log("Creating bucket")
        endpoint = "buckets/{}".format(bucket_id)
        data = {
            "client": self.client_name,
            "type": "app.editor.activity",
            "hostname": self.hostname,
        }
        resp = self._session.post(self._make_url(endpoint), json=data)
        return resp.json()

    def delete_bucket(self, bucket_id: str) -> Any:
        if self.debug:
            utils.log("Deleting bucket")
        endpoint = "buckets/{}?force=1".format(bucket_id)
        resp = self._session.delete(self._make_url(endpoint))
        return resp.json()

    def ensure_bucket(self, bucket_id: str) -> None:
        if self.debug:
            utils.log("Ensuring bucket exists")
        bucket = self.get_bucket(bucket_id)
        bucket_exists = "id" in bucket
        if not bucket_exists:
            self.create_bucket(bucket_id)

    def connect(self, bucket_id: str) -> bool:
        if not self.check():
            return False
        try:
            self.ensure_bucket(bucket_id)
        except requests.RequestException as err:
            if self.debug:
                utils.log("could not set up bucket: {}".format(err))
            return False
        return True

    def heartbeat(
        self, bucket_id: str, event_data: Dict[str, Any], pulsetime: int = 30
    ) -> bool:
        now = datetime.now(timezone.utc)

        if not self._rate_limited(now):
            return True

        if self.debug:
            utils.log("Heartbeat")

        endpoint = "buckets/{}/heartbeat?pulsetime={}".format(bucket_id, pulsetime)
        data = {
            "timestamp": now.isoformat(),
            "duration": 0,
            "data": event_data,
        }
        try:
            self._session.post(self._make_url(endpoint), json=data)
        except requests.RequestException as err:
            if self.debug:
                utils.log("heartbeat failed: {}".format(err))
            return False

        self._last_heartbeat = now
        return True
