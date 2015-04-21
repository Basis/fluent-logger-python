# -*- coding: utf-8 -*-

from __future__ import print_function
import socket
import threading
import time

import msgpack
import ujson as json

_global_sender = None


def setup(tag, **kwargs):
    global _global_sender
    _global_sender = FluentSender(tag, **kwargs)


def get_global_sender():
    return _global_sender


class FluentSender(object):
    def __init__(self,
                 tag,
                 host='localhost',
                 port=24224,
                 bufmax=1 * 1024 * 1024,
                 timeout=3.0,
                 verbose=False,
                 pack_msg=False,
                 udp=False):

        self.tag = tag
        self.host = host
        self.port = port
        self.bufmax = bufmax
        self.timeout = timeout
        self.verbose = verbose
        self.udp = udp
        self.pack_msg = pack_msg

        self.socket = None
        self.pendings = None
        self.lock = threading.Lock()

        try:
            self._reconnect()
        except Exception:
            # will be retried in emit()
            self._close()

    def emit(self, label, data):
        cur_time = int(time.time())
        self.emit_with_time(label, cur_time, data)

    def emit_with_time(self, label, timestamp, data):
        bytes_ = self._make_packet(label, timestamp, data)
        self._send(bytes_)

    def _make_packet(self, label, timestamp, data):
        if label:
            tag = '.'.join((self.tag, label))
        else:
            tag = self.tag
        packet = data
        packet['label'] = tag
        packet['time'] = timestamp
        if self.verbose:
            print(packet)
        if self.pack_msg:
            return msgpack.packb(packet)
        else:
            if self.udp:
                return json.dumps(packet)
            else:
                # tcp needs a delimiter
                return '%s\n' % json.dumps(packet)

    def _send(self, bytes_):
        self.lock.acquire()
        try:
            if self.udp:
                self.socket.sendto(bytes_, (self.host, self.port))
            else:
                self._send_internal(bytes_)
        finally:
            self.lock.release()

    def _send_internal(self, bytes_):
        # buffering
        if self.pendings:
            self.pendings += bytes_
            bytes_ = self.pendings

        try:
            # reconnect if possible
            self._reconnect()

            # send message
            self.socket.sendall(bytes_)

            # send finished
            self.pendings = None
        except Exception:
            # close socket
            self._close()
            # clear buffer if it exceeds max bufer size
            if self.pendings and (len(self.pendings) > self.bufmax):
                # TODO: add callback handler here
                self.pendings = None
            else:
                self.pendings = bytes_

    def _reconnect(self):
        if not self.socket:
            if self.udp:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            elif self.host.startswith('unix://'):
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.settimeout(self.timeout)
                sock.connect(self.host[len('unix://'):])
            else:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(self.timeout)
                sock.connect((self.host, self.port))
            self.socket = sock

    def _close(self):
        if self.socket:
            self.socket.close()
        self.socket = None
