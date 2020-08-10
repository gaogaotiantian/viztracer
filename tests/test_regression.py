import unittest
import codesnap

class TestIssue1:
    def test_datetime(self):
        import datetime

        snap = codesnap.CodeSnap()
        snap.start()
        from datetime import timedelta
        a = timedelta(hours = 5)
        snap.end()
        snap.parse()
        snap.generate_json()