# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import unittest
import logging
from viztracer import VizTracer, VizLoggingHandler


class TestLogging(unittest.TestCase):
    def test_handler(self):
        tracer = VizTracer()
        handler = VizLoggingHandler()
        handler.setTracer(tracer)
        logging.basicConfig(handlers = [handler])
        tracer.start()
        logging.warning("lol")
        tracer.stop()
        entries = tracer.parse()
        self.assertGreater(entries, 10)
        logging.getLogger().removeHandler(handler)

    def test_notracer(self):
        tracer = VizTracer()
        handler = VizLoggingHandler()
        logging.basicConfig(handlers = [handler])
        tracer.start()
        with self.assertRaises(Exception):
            logging.warning("lol")
        tracer.stop()