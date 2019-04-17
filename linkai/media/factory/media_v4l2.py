#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2018/12/20 下午4:36
# @Author  : zhen_jiang
# @File    : media_v412.py

import gi
import logging
from .media import Media

gi.require_version('Gst', '1.0')

from gi.repository import GObject, Gst

log = logging.getLogger(__name__)


# v4l2只出本地摄像头的rgb流
class MediaV4L2(Media):
    def __init__(self, stream_id, uri, listener):
        Media.__init__(self, stream_id, uri, listener)

    def __del__(self):
        pass

    def start(self):
        Media.start(self)
        # Create elements
        src = Gst.ElementFactory.make('v4l2src', None)
        convert = Gst.ElementFactory.make("videoconvert", None)
        sink = Gst.ElementFactory.make('appsink', None)
        caps = Gst.caps_from_string("video/x-raw, format=RGBA")
        sink.set_property("caps", caps)
        # Add elements to pipeline
        self.pipeline.add(src)
        self.pipeline.add(convert)
        self.pipeline.add(sink)
        # Set properties
        src.set_property('device', "/dev/video0")
        sink.set_property('emit-signals', True)
        # turns off sync to make decoding as fast as possible
        sink.set_property('sync', False)
        sink.connect('new-sample', self.on_frame_cpu)
        # Link elements
        src.link(convert)
        convert.link(sink)
        # Creates a bus and set callbacks to receive errors
        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message::eos", self.on_eos)
        bus.connect("message::error", self.on_error)
        self.pipeline.set_state(Gst.State.PLAYING)
