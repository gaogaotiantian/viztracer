from unittest import TestCase


class BaseTmpl(TestCase):
    def setUp(self):
        print("{} start".format(self.id()))

    def tearDown(self):
        print("{} finish".format(self.id()))
