import unittest

from .api import ActivityWatchApi


class ApiTest(unittest.TestCase):
    def setUp(self):
        self.api = ActivityWatchApi("test_client", "localhost", 5600, 5)

    def test_check_is_alive(self):
        self.assertTrue(self.api.check())

    def test_check_has_bucket(self):
        bucket_name = "test_bucket"
        bucket = self.api.get_bucket(bucket_name)
        self.assertFalse('id' in bucket)

    def test_create_bucket(self):
        bucket_name = "test_bucket"

        self.api.create_bucket(bucket_name)

        bucket = self.api.get_bucket(bucket_name)
        self.assertTrue('id' in bucket)
        self.assertEqual(bucket.get('id'), bucket_name)

        self.api.delete_bucket(bucket_name)

    def test_ensure_bucket(self):
        bucket_name = "test_bucket"

        bucket = self.api.get_bucket(bucket_name)
        self.assertFalse('id' in bucket)

        self.api.ensure_bucket(bucket_name)

        bucket = self.api.get_bucket(bucket_name)
        self.assertTrue('id' in bucket)
        self.assertEqual(bucket.get('id'), bucket_name)

        self.api.delete_bucket(bucket_name)

    def test_heartbeat(self):
        pass
