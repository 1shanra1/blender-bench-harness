"""Preserve native events and record when each line reached our driver."""
import json
from pathlib import Path
import time


class EventLog:
    def __init__(self, path):
        self.path = Path(path)
        self.line_number = 0

    def __enter__(self):
        self.events = self.path.open('w')
        self.timestamps = self.path.with_suffix('.timestamps.jsonl').open('w')
        return self

    def write(self, line):
        received_at_ns = time.time_ns()
        self.line_number += 1
        self.events.write(line)
        self.timestamps.write(json.dumps({
            'line_number': self.line_number,
            'received_at_unix_ns': received_at_ns,
        }) + '\n')

    def flush(self):
        self.events.flush()
        self.timestamps.flush()

    def __exit__(self, *exception):
        self.events.close()
        self.timestamps.close()
