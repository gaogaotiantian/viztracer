class ProgressBar:
    def __init__(self, pre_string="", post_string=""):
        # print pre_string <bar> post_string
        self.pre_string = pre_string
        self.post_string = post_string
        self.bar_granularity = 5
        # Percentage
        self.progress = 0
    
    def _bar(self):
        finish_part = int(self.progress / self.bar_granularity)
        left_part = int(100 / self.bar_granularity) - finish_part
        return "[" + "#" * finish_part + "." * left_part + "] "\
                   + str(int(self.progress)) + "%"
    
    def update(self, progress):
        if progress * 100 - self.progress >= 1:
            # only update after 1% change
            self.progress = int(progress * 100)
            print('\r{} {} {}'.format(self.pre_string, self._bar(), self.post_string), end="")
            if self.progress == 100:
                print("")
