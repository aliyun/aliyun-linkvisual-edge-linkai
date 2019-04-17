# -*- coding: UTF-8 -*-#

import gi
import logging
from .media import Media
import os

gi.require_version('Gst', '1.0')

from gi.repository import Gst

log = logging.getLogger(__name__)

'''
GST_DEBUG=4 gst-launch-1.0 -v filesrc location=a.mp4 ! qtdemux ! h264parse ! nvdec_h264 ! nvvidconv ! 'video/x-raw(memory:NVMM),format=BGRx' ! fakesink
GST_DEBUG=4 gst-launch-1.0 -v rtmpsrc location=rtmp://192.168.6.50:1935/stream/zhouhao ! flvdemux ! h264parse ! nvdec_h264 ! nvvidconv ! 'video/x-raw(memory:NVMM),format=BGRx' ! fakesink
GST_DEBUG=4 gst-launch-1.0 -v uridecodebin uri=rtmp://192.168.6.50:1935/stream/zhouhao ! nvvidconv ! 'video/x-raw(memory:NVMM),format=BGRx' ! fakesink
'''

'''
avi测试
gst-launch-1.0 filesrc location="/AII/ladc/snapshot/I05/20180808/IMAG2363.AVI" ! avidemux ! h264parse ! nvdec_h264 ! nvvidconv ! 'video/x-raw(memory:NVMM),format=BGRx' ! fakesink
'''


# 流媒体只出RGB数据
class MediaGpu(Media):
    def __init__(self, stream_id, uri, listener):
        Media.__init__(self, stream_id, uri, listener)

    def __del__(self):
        pass

    def start(self):
        Media.start(self)
        if self.uri.startswith("rtmp://"):
            source = Gst.ElementFactory.make("rtmpsrc", None)
            source.set_property("location", self.uri)
            demux = Gst.ElementFactory.make("flvdemux", None)
        elif self.uri.startswith("rtsp://"):
            source = Gst.ElementFactory.make("rtspsrc", None)
            source.set_property("location", self.uri)
            demux = Gst.ElementFactory.make("rtph264depay", None)
        elif self.uri.endswith(".mp4") or self.uri.endswith(".MP4") or self.uri.endswith(".m4v") or self.uri.endswith(
                ".M4V"):
            source = Gst.ElementFactory.make("filesrc", None)
            source.set_property("location", self.uri)
            demux = Gst.ElementFactory.make("qtdemux", None)
        elif self.uri.endswith(".avi") or self.uri.endswith(".AVI"):
            source = Gst.ElementFactory.make("filesrc", None)
            source.set_property("location", self.uri)
            demux = Gst.ElementFactory.make("avidemux", None)
        else:
            log.error("media start,not support uri={}".format(self.uri))
            return
        queue = Gst.ElementFactory.make("queue2", None)
        queue.set_property("max-size-buffers", 5)
        h264parse = Gst.ElementFactory.make("h264parse", None)
        h264parse.set_property("config-interval", 1)
        nvdec_h264 = Gst.ElementFactory.make("nvdec_h264", None)
        device = 0
        if os.environ.get("GPU_ID") is not None:
            device = int(os.environ.get("GPU_ID"))
        nvdec_h264.set_property("gpu-id", device)
        gpu_convert = Gst.ElementFactory.make("nvvidconv", None)
        gpu_convert.set_property("gpu-id", device)
        gpu_sink = Gst.ElementFactory.make("appsink", None)
        gpu_sink.set_property("emit-signals", True)
        gpu_sink.set_property("max-buffers", 1)
        caps = Gst.caps_from_string("video/x-raw(memory:NVMM), format=(string){RGBA}")
        gpu_sink.set_property("caps", caps)
        self.pipeline.add(source)
        self.pipeline.add(demux)
        self.pipeline.add(queue)
        self.pipeline.add(h264parse)
        self.pipeline.add(nvdec_h264)
        self.pipeline.add(gpu_convert)
        self.pipeline.add(gpu_sink)

        if self.uri.startswith("rtsp://"):
            source.connect("pad-added", self.on_pad_added, demux)
            demux.link(queue)
        else:
            source.link(demux)
            demux.connect("pad-added", self.on_pad_added, queue)
        queue.link(h264parse)
        h264parse.link(nvdec_h264)
        nvdec_h264.link(gpu_convert)
        gpu_convert.link(gpu_sink)
        gpu_sink.connect("new-sample", self.on_frame_gpu)
        # Creates a bus and set callbacks to receive errors
        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message::eos", self.on_eos)
        bus.connect("message::error", self.on_error)
        self.pipeline.set_state(Gst.State.PLAYING)

    # def start(self):
    #     Media.start(self)
    #     if not Gst.uri_is_valid(self.uri):
    #         self.uri = Gst.filename_to_uri(self.uri)
    #     source = Gst.ElementFactory.make("uridecodebin", None)
    #     source.set_property("uri", self.uri)
    #     # gpu
    #     gpu_convert = Gst.ElementFactory.make("nvvidconv", None)
    #     gpu_sink = Gst.ElementFactory.make("appsink", None)
    #     gpu_sink.set_property("emit-signals", True)
    #     gpu_sink.set_property("max-buffers", 1)
    #     caps = Gst.caps_from_string("video/x-raw(memory:NVMM), format=(string){RGBA}")
    #     gpu_sink.set_property("caps", caps)
    #     self.pipeline.add(source)
    #     self.pipeline.add(gpu_convert)
    #     self.pipeline.add(gpu_sink)
    #     source.connect("pad-added", self.on_pad_added, gpu_convert)
    #     gpu_convert.link(gpu_sink)
    #     gpu_sink.connect("new-sample", self.on_frame_gpu)
    #     # Creates a bus and set callbacks to receive errors
    #     bus = self.pipeline.get_bus()
    #     bus.add_signal_watch()
    #     bus.connect("message::eos", self.on_eos)
    #     bus.connect("message::error", self.on_error)
    #     self.pipeline.set_state(Gst.State.PLAYING)

    ''' 没有码流会崩溃
    def start(self):
        Media.start(self)
        source = Gst.ElementFactory.make("rtmpsrc", None)
        source.set_property("location", self.uri)
        flvdemux = Gst.ElementFactory.make("flvdemux", None)
        queue = Gst.ElementFactory.make("queue2", None)
        queue.set_property("max-size-buffers", 5)
        h264parse = Gst.ElementFactory.make("h264parse", None)
        # BGRX
        gpu_nvdec_h264 = Gst.ElementFactory.make("nvdec_h264", None)
        gpu_convert = Gst.ElementFactory.make("nvvidconv", None)
        gpu_sink = Gst.ElementFactory.make("appsink", None)
        gpu_sink.set_property("emit-signals", True)
        gpu_sink.set_property("max-buffers", 1)
        caps = Gst.caps_from_string("video/x-raw(memory:NVMM), format=(string){BGRx}")
        gpu_sink.set_property("caps", caps)

        self.pipeline.add(source)
        self.pipeline.add(flvdemux)
        self.pipeline.add(queue)
        self.pipeline.add(h264parse)
        self.pipeline.add(gpu_nvdec_h264)
        self.pipeline.add(gpu_convert)
        self.pipeline.add(gpu_sink)

        source.link(flvdemux)
        flvdemux.connect("pad-added", self.on_pad_added, queue)
        queue.link(h264parse)
        h264parse.link(gpu_nvdec_h264)
        gpu_nvdec_h264.link(gpu_convert)
        gpu_convert.link(gpu_sink)
        gpu_sink.connect("new-sample", self.on_frame_gpu)
        # Creates a bus and set callbacks to receive errors
        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message::eos", self.on_eos)
        bus.connect("message::error", self.on_error)
        self.pipeline.set_state(Gst.State.PLAYING)
    '''

    ''' 测试过不崩溃
        def start(self):
        Media.start(self)
        source = Gst.ElementFactory.make("rtmpsrc", None)
        source.set_property("location", self.uri)
        flvdemux = Gst.ElementFactory.make("flvdemux", None)
        queue = Gst.ElementFactory.make("queue2", None)
        queue.set_property("max-size-buffers", 5)
        h264parse = Gst.ElementFactory.make("h264parse", None)
        # BGRX
        gpu_nvdec_h264 = Gst.ElementFactory.make("decodebin", None)
        gpu_convert = Gst.ElementFactory.make("nvvidconv", None)
        gpu_sink = Gst.ElementFactory.make("appsink", None)
        gpu_sink.set_property("emit-signals", True)
        gpu_sink.set_property("max-buffers", 1)
        caps = Gst.caps_from_string("video/x-raw(memory:NVMM), format=(string){BGRx}")
        gpu_sink.set_property("caps", caps)

        self.pipeline.add(source)
        self.pipeline.add(flvdemux)
        self.pipeline.add(queue)
        self.pipeline.add(h264parse)
        self.pipeline.add(gpu_nvdec_h264)
        self.pipeline.add(gpu_convert)
        self.pipeline.add(gpu_sink)

        source.link(flvdemux)
        flvdemux.connect("pad-added", self.on_pad_added, queue)
        queue.link(h264parse)
        h264parse.link(gpu_nvdec_h264)
        gpu_nvdec_h264.connect("pad-added", self.on_pad_added, gpu_convert)
        # gpu_nvdec_h264.link(gpu_convert)
        gpu_convert.link(gpu_sink)
        gpu_sink.connect("new-sample", self.on_frame_gpu)
        # Creates a bus and set callbacks to receive errors
        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message::eos", self.on_eos)
        bus.connect("message::error", self.on_error)
        self.pipeline.set_state(Gst.State.PLAYING)
    '''
