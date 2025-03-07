# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import multiprocessing as mp

from viztracer.decorator import trace_and_save


from .base_tmpl import BaseTmpl


@trace_and_save(output_dir="/tmp/")
def _foo():
    print("foo")


class TestDaemon(BaseTmpl):

    def test_daemon(self):
        # use fork to create a daemon process
        mp.set_start_method("fork")
        p = mp.Process(target=_foo, daemon=True)
        p.daemon = True
        p.start()
        p.join()
        # get return code of the process
        self.assertEqual(p.exitcode, 0)
