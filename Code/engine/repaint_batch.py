"""Bounded, reusable painter commands for large world repaints."""


class RepaintBatch:
    def __init__(self, capacity=2048):
        self.commands = [[None, [0, 0]] for _ in range(capacity)]
        self.count = 0
        self.target = None

    def begin(self, target):
        self.target = target
        self.count = 0
        return self

    def append(self, command):
        slot = self.commands[self.count]
        slot[0] = command[0]
        slot[1][0], slot[1][1] = command[1]
        self.count += 1
        if self.count == len(self.commands):
            self.flush()

    def flush(self):
        if self.count:
            commands = self.commands if self.count == len(self.commands) else self.commands[:self.count]
            self.target.blits(commands, doreturn=False)
            for command in commands:
                command[0] = None
            self.count = 0

    def finish(self):
        self.flush()
        self.target = None

