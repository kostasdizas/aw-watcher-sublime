import json
import socket
import requests
from datetime import datetime, timezone

from . import utils


class ActivityWatchApi(object):

    def __init__(self):
        utils.log("ActivityWatchApi initializing")
        self.debug = False
        self._last_heartbeat = datetime.min.replace(tzinfo=timezone.utc)

    def setup(self, client_name, host, port, min_seconds):
        self.url = "http://{}:{}".format(host, port)
        self.client_name = client_name
        self.hostname = socket.gethostname()
        self.min_seconds = min_seconds

    def enable_debugging(self):
        self.debug = True
        utils.log("API debugging enabled")

    def disable_debugging(self):
        if self.debug:
            utils.log("API debugging disabled")
        self.debug = False

    def _make_url(self, endpoint):
        return "{}/api/0/{}".format(self.url, endpoint)

    def _rate_limited(self, now):
        return (now - self._last_heartbeat).total_seconds() > self.min_seconds

    def check(self):
        if self.debug:
            utils.log("Checking server connection")
        headers = {"Content-type": "application/json"}
        try:
            requests.get(self._make_url(""), headers=headers)
            return True
        except requests.RequestException:
            utils.log("could not connect")
            return False

    def get_bucket(self, bucket_id):
        if self.debug:
            utils.log("Retrieving bucket")
        endpoint = 'buckets/{}'.format(bucket_id)
        headers = {'content-type': 'application/json'}
        resp = requests.get(self._make_url(endpoint), headers=headers)
        return json.loads(resp.text)

    def create_bucket(self, bucket_id):
        if self.debug:
            utils.log("Creating bucket")
        endpoint = 'buckets/{}'.format(bucket_id)
        data = {
            'client': self.client_name,
            'type': 'app.editor.activity',
            'hostname': self.hostname
        }
        headers = {'content-type': 'application/json'}
        resp = requests.post(self._make_url(endpoint),
                             data=json.dumps(data), headers=headers)
        return json.loads(resp.text)

    def delete_bucket(self, bucket_id):
        if self.debug:
            utils.log("Deleting bucket")
        endpoint = 'buckets/{}?force=1'.format(bucket_id)
        resp = requests.delete(self._make_url(endpoint))
        return json.loads(resp.text)

    def ensure_bucket(self, bucket_id):
        if self.debug:
            utils.log("Ensuring bucket exists")
        bucket = self.get_bucket(bucket_id)
        bucket_exists = 'id' in bucket
        if not bucket_exists:
            self.create_bucket(bucket_id)

    def heartbeat(self, bucket_id, event_data, pulsetime=30):
        now = datetime.now(timezone.utc)

        if not self._rate_limited(now):
            return

        if self.debug:
            utils.log("Heartbeat")

        endpoint = 'buckets/{}/heartbeat?pulsetime={}'.format(bucket_id,
                                                              pulsetime)
        data = {
            'timestamp': now.isoformat(),
            'duration': 0,
            'data': event_data,
        }
        headers = {'content-type': 'application/json'}
        resp = requests.post(self._make_url(endpoint),
                             data=json.dumps(data), headers=headers)
        self._last_heartbeat = now
        return resp
