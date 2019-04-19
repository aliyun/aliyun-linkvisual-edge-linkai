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
import numpy
import logging
from ctypes import *

# ll = cdll.LoadLibrary
# lib = ll("./libpycall.so")

gi.require_version('Gst', '1.0')

from gi.repository import GObject, Gst

log = logging.getLogger(__name__)


class _MapInfo(Structure):
    _fields_ = [
        ('memory', c_void_p),
        ('flags', c_int),
        ('data', c_void_p)]
    # we don't care about the rest


class Media(object):
    """ 流媒体基类

    已经对各种回调媒体类型的数据进行处理，例如h264,rgba
    Attributes:
        uri: 流媒体URI，支持本地文件,rtsp,rtmp
        listener: 监听类，媒体回调数据会通过Listener的on_frame_h264等回调
        stream_id: 流媒体标识Id
        pipeline: gstreamer的一个pipline
    """

    def __init__(self, stream_id, uri, listener):
        self.uri = uri
        self.listener = listener
        self.stream_id = stream_id
        self.pipeline = None
        self.is_first_frame_cpu = True
        self.is_first_frame_h264 = True
        self.is_first_frame_nvidia_gpu = True

    def get_uri(self):
        return self.uri

    def __del__(self):
        pass

    def start(self):
        """ 拉流启动，具体的Pipline组成由各个子类自己实现,子类的回调实现必须在父类这里实现，例如on_frame_h264,便于各个子类复用 """
        self.is_first_frame_cpu = True
        self.is_first_frame_h264 = True
        self.is_first_frame_nvidia_gpu = True

        if self.pipeline is not None:
            self.pipeline.set_state(Gst.State.NULL)

        self.pipeline = Gst.Pipeline.new(None)

    def stop(self):
        """ 拉流关闭 """
        self.pipeline.set_state(Gst.State.NULL)

    def on_frame_cpu(self, sink):
        """ 子类cpu数据回调处 """
        sample = sink.emit("pull-sample")
        buf = sample.get_buffer()
        caps = sample.get_caps()
        height = caps.get_structure(0).get_value('height')
        width = caps.get_structure(0).get_value('width')
        format_type = caps.get_structure(0).get_value('format')
        mem_type = caps.get_structure(0).get_name()
        pts = buf.pts
        dts = buf.dts
        duration = buf.duration

        # buf.map 消耗4ms左右 1920*1080*NV12
        (result, map_info) = buf.map(Gst.MapFlags.READ)

        if self.is_first_frame_cpu:
            log.info("first cpu frame accept, stream_id[%s] height[%d] width[%d] type[%s] mem[%s]"
                     % (self.stream_id, height, width, format_type, mem_type))
            self.is_first_frame_cpu = False

        if result:
            # numpy.frombuffer 基本不耗时 1ms以下
            arr = numpy.frombuffer(map_info.data, dtype=numpy.uint8)
            if hasattr(self.listener, "on_frame_cpu"):
                self.listener.on_frame_cpu(array=arr.reshape((1, height, width, 4)),
                                           height=height, width=width, format_type=format_type,
                                           raw_type=mem_type, pts=pts, dts=dts, duration=duration)

        buf.unmap(map_info)
        return Gst.FlowReturn.OK

    def on_frame_h264(self, sink):
        """ 子类h264数据回调处 """
        sample = sink.emit("pull-sample")
        buf = sample.get_buffer()
        caps = sample.get_caps()
        height = caps.get_structure(0).get_value('height')
        width = caps.get_structure(0).get_value('width')
        format_type = caps.get_structure(0).get_value('format')
        mem_type = caps.get_structure(0).get_name()
        ok, numerator, denominator = caps.get_structure(0).get_fraction("framerate")
        if ok and hasattr(self.listener, "set_framerate"):
            framerate = numerator / denominator
            if framerate > 0:
                self.listener.set_framerate(numerator / denominator)

        # buf.map 消耗4ms左右 1920*1080*NV12
        (result, map_info) = buf.map(Gst.MapFlags.READ)

        if self.is_first_frame_h264:
            log.info("first h264 frame accept, stream_id[%s] height[%d] width[%d] mem[%s]"
                     % (self.stream_id, height, width, mem_type))
            self.is_first_frame_h264 = False
        if hasattr(self.listener, "on_frame_h264"):
            self.listener.on_frame_h264(data=map_info.data,
                                        height=height, width=width, format_type=format_type,
                                        raw_type=mem_type)
        buf.unmap(map_info)
        return Gst.FlowReturn.OK

    def on_frame_gpu(self, sink):
        """ 子类gpu数据回调处 """
        # NvBufSurface * nvsurface = *((NvBufSurface **) map.data);
        # frame.data = (char *)nvsurface->buf_data[0];
        sample = sink.emit("pull-sample")
        buf = sample.get_buffer()
        caps = sample.get_caps()
        height = caps.get_structure(0).get_value('height')
        width = caps.get_structure(0).get_value('width')
        format_type = caps.get_structure(0).get_value('format')
        mem_type = caps.get_structure(0).get_name()
        if mem_type.find('NVMM') == -1:
            mem_type = mem_type + "(memory:NVMM)"
        pts = buf.pts
        dts = buf.dts
        duration = buf.duration

        (result, map_info) = buf.map(Gst.MapFlags.READ)
        if self.is_first_frame_nvidia_gpu:
            log.info("first gpu frame accept, stream_id[%s] height[%d] width[%d] mem[%s]"
                     % (self.stream_id, height, width, mem_type))
            self.is_first_frame_nvidia_gpu = False
        addr = map_info.__hash__()
        c_map_info = _MapInfo.from_address(addr)
        # lib.foo2(c_long(c_map_info.data))
        if hasattr(self.listener, "on_frame_gpu"):
            self.listener.on_frame_gpu(data=c_map_info.data,
                                       height=height, width=width, format_type=format_type,
                                       raw_type=mem_type, pts=pts, dts=dts, duration=duration)
        buf.unmap(map_info)
        return Gst.FlowReturn.OK

    def on_eos(self, bus, msg):
        """ 拉流结束,一般为本地文件 """
        log.info("on_eos stream_id[%s]" % self.stream_id)
        if hasattr(self.listener, "on_eos"):
            self.listener.on_eos(self, bus, msg)

    def on_error(self, bus, msg):
        """ 拉流错误回调 """
        err, debug = msg.parse_error()
        log.error("on_error stream_id[{}] err[{}] debug[{}]".format(self.stream_id, err, debug))
        if hasattr(self.listener, "on_error"):
            self.listener.on_error(self, bus, msg)

    def on_pad_added(self, element, pad, queue):
        """ 只处理视频，音频及其它不做处理 """
        string = pad.query_caps(None).to_string()
        log.debug("on pad added name={} str={}".format(element.get_name(), string))
        if string.find('video') != -1:
            pad.link(queue.get_static_pad("sink"))
        else:
            log.warning("stream source error string={} ".format(string))
