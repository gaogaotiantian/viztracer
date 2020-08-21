class Counter:
    def __init__(self, callback, name, value={}):
        self._name = name
        self._callback = callback

    def _update(self, d):
        if self._callback:
            self._callback(self._name, d)

    def update(self, *args):
        if len(args) == 1:
            if type(args[0]) is dict:
                self._update(args[0])
            else:
                print(type(args[0]))
                raise Exception("Counter.update() takes a dict update(dict) or a key value pair set_value(key, value)")
        elif len(args) == 2:
            if type(args[0]) is str:
                try:
                    val = float(args[1])
                    self._update({args[0]: val})
                except Exception:
                    raise Exception("Counter.update() takes a dict update(dict) or a key value pair set_value(key, value)")
