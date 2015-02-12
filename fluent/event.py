# -*- coding: utf-8 -*-

from datetime import datetime
from fluent import sender


class Event(object):
    def __init__(self, label, data):
        """ we have defaults for the following keys:
        * time (now())
        * label (the arg)

        values in the data dict overwrite defaults
        """
        assert isinstance(data, dict), 'data must be a dict'
        sender_ = sender.get_global_sender()
        timestamp = data.get('time',
            datetime.now().strftime('%Y-%m-%dT%H:%M:%S'))
        label = data.get('label', label)
        sender_.emit_with_time(label, timestamp, data)
