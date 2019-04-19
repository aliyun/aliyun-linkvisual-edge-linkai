# -*- coding: UTF-8 -*-#
#
# Copyright (c) 2014-2018 Alibaba Group. All rights reserved.
# License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
#
import gi
import logging
from .media import Media

gi.require_version('Gst', '1.0')

from gi.repository import Gst

log = logging.getLogger(__name__)


# 流媒体只出RGBA数据
class MediaCpu(Media):
    def __init__(self, stream_id, uri, listener):
        Media.__init__(self, stream_id, uri, listener)

    def __del__(self):
        pass

    def start(self):
        Media.start(self)
        if not Gst.uri_is_valid(self.uri):
            self.uri = Gst.filename_to_uri(self.uri)
        source = Gst.ElementFactory.make("uridecodebin", None)
        source.set_property("uri", self.uri)
        queue = Gst.ElementFactory.make("queue2", None)
        queue.set_property("max-size-buffers", 5)
        convert = Gst.ElementFactory.make("videoconvert", None)
        sink = Gst.ElementFactory.make("appsink", None)
        sink.set_property("emit-signals", True)
        sink.set_property("max-buffers", 1)
        caps = Gst.caps_from_string("video/x-raw, format=(string){RGBA}")
        sink.set_property("caps", caps)
        self.pipeline.add(source)
        self.pipeline.add(queue)
        self.pipeline.add(convert)
        self.pipeline.add(sink)
        source.connect("pad-added", self.on_pad_added, queue)
        queue.link(convert)
        convert.link(sink)
        sink.connect("new-sample", self.on_frame_cpu)
        # Creates a bus and set callbacks to receive errors
        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message::eos", self.on_eos)
        bus.connect("message::error", self.on_error)
        self.pipeline.set_state(Gst.State.PLAYING)
