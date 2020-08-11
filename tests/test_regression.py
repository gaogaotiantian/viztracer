import unittest
import codesnap


class TestIssue1(unittest.TestCase):
    def test_datetime(self):
        snap = codesnap.CodeSnap()
        snap.start()
        from datetime import timedelta
        timedelta(hours=5)
        snap.stop()
        snap.parse()
        snap.generate_json()

        snap = codesnap.CodeSnap(tracer="python")
        snap.start()
        from datetime import timedelta
        timedelta(hours=5)
        snap.stop()
        snap.parse()
        snap.generate_json()