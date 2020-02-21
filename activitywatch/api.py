import json
import socket
import requests
from datetime import datetime

from . import utils


class ActivityWatchApi(object):
    _last_heartbeat = datetime.now()
    freq = 10

    def __init__(self, client_name, host, port, freq):
        self.url = "http://{}:{}".format(host, port)
        self.client_name = client_name
        self.hostname = socket.gethostname()
        self.freq = freq

    def _make_url(self, endpoint):
        return "{}/api/0/{}".format(self.url, endpoint)

    def _rate_limited(self, now):
        return (now - self._last_heartbeat).total_seconds() > self.freq

    def check(self):
        if self.debug:
            utils.log("Checking server connection")
        headers = {"Content-type": "application/json"}
        try:
            requests.get(self._make_url(""), headers=headers)
            self.connected = True
        except requests.RequestException:
            self.connected = False
            utils.log("could not connect")

        return self.connected

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
        now = datetime.now()

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
