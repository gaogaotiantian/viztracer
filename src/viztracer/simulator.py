# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import sys
import os
import argparse
try:
    import readline
except ImportError:
    pass

from .prog_snapshot import ProgSnapshot


class Simulator:
    def __init__(self, json_string, no_clear=False, extra_newline=False):
        try:
            from rich.console import Console
            from rich.syntax import Syntax
            self.console = Console()

            def p(s):
                syntax = Syntax(s, "python", theme="monokai")
                self.console.print(syntax, soft_wrap=True)

            self.print = p
        except ImportError:
            self.print = print
        self.snapshot = ProgSnapshot(json_string, self.print)
        if not self.snapshot.valid:
            exit(1)
        self.no_clear = no_clear
        self.extra_newline = extra_newline

    def start(self):
        self.clear()
        self.snapshot.show()
        while True:
            try:
                cmd = input(">>> ")
                if self.extra_newline:
                    print("")
                self.parse_cmd(cmd)
            except EOFError:
                exit(0)

    def clear(self):
        if not self.no_clear:
            os.system("cls" if os.name == "nt" else "clear")

    def parse_cmd(self, cmd):
        args = cmd.split()
        if not args:
            return
        success = False
        if args[0] == "s":
            success, err_msg = self.snapshot.step()
        elif args[0] == "sb":
            success, err_msg = self.snapshot.step_back()
        elif args[0] == "n":
            success, err_msg = self.snapshot.next()
        elif args[0] == "nb":
            success, err_msg = self.snapshot.next_back()
        elif args[0] == "r":
            success, err_msg = self.snapshot.func_return()
        elif args[0] == "rb":
            success, err_msg = self.snapshot.func_return_back()
        elif args[0] == "t":
            if len(args) == 1:
                success, err_msg = self.snapshot.print_timestamp()
                return
            elif len(args) == 2:
                success, err_msg = self.snapshot.goto_timestamp(float(args[1]))
            else:
                success, err_msg = False, "t takes 1 or no argument"
        elif args[0] == "u":
            success, err_msg = self.snapshot.up()
        elif args[0] == "d":
            success, err_msg = self.snapshot.down()
        elif args[0] == "w":
            success, err_msg = self.snapshot.where()
            return
        elif args[0] == "tid":
            if len(args) == 1:
                success, err_msg = self.snapshot.list_tid()
                return
            elif len(args) == 2:
                try:
                    tid = int(args[1])
                    success, err_msg = self.snapshot.goto_tid(tid)
                except ValueError:
                    print("tid needs to be an integer")
                    return
            else:
                success, err_msg = False, "tid takes 1 or no argument"
        elif args[0] == "pid":
            if len(args) == 1:
                success, err_msg = self.snapshot.list_pid()
                return
            elif len(args) == 2:
                try:
                    pid = int(args[1])
                    success, err_msg = self.snapshot.goto_pid(pid)
                except ValueError:
                    print("tid needs to be an integer")
                    return
            else:
                success, err_msg = False, "pid takes 1 or no argument"
        elif args[0] in ["arg", "args"]:
            success, err_msg = self.snapshot.print_args()
            return
        elif args[0] == "counter":
            success, err_msg = self.snapshot.print_counter()
            return
        elif args[0] == "object":
            success, err_msg = self.snapshot.print_object()
            return
        elif args[0] in ["quit", "exit", "q"]:
            exit(0)
        else:
            print("Invalid command: {}".format(cmd))
            return

        if success:
            self.clear()
            self.snapshot.show()
        else:
            print(err_msg)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file", nargs=1)
    parser.add_argument("--no_clear", action="store_true", default=False)
    parser.add_argument("--extra_newline", action="store_true", default=False)

    options = parser.parse_args(sys.argv[1:])

    filename = options.file[0]
    with open(filename) as f:
        s = f.read()

    sim = Simulator(s, no_clear=options.no_clear, extra_newline=options.extra_newline)
    sim.start()


if __name__ == '__main__':
    main()
