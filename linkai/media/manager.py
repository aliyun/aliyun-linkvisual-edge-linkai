# -*- coding: UTF-8 -*-#
# a singleton sentinel value for parameter defaults
# _sentinel = object()
import threading
import logging

import gi
from .factory.media_factory import MediaFactory

gi.require_version('Gst', '1.0')

from gi.repository import GObject, Gst

log = logging.getLogger(__name__)


class MediaManager:
    """ 流媒体管理，单件实例media_manager

    对基类为Media的媒体类进行管理
    Attributes:
        dict_streams: 流媒体集合MAP
    """

    def __init__(self):
        """类初始化，启动gst线程进行流媒体消息回调"""
        GObject.threads_init()
        Gst.init(None)

        self.dict_streams = {}

    def gst_bus_loop_start(self):
        # 启用一个线程驱动 GObject 这样才能接收到bus上on_msg on_error回调
        threading.Thread(target=lambda: GObject.MainLoop().run(), name="GSTBusLoop").start()

    def open_stream(self, stream_id, uri, listener=None, stream_type="cpu_h264"):
        """ 打开流媒体
        开启流媒体播放，会有不同帧数据进行通过listener的方法回调,例如on_frame_h264

        参数
        ----------
        stream_id : str
            媒体ID,确保唯一
        uri : str
            流媒体播放的uri,例如rtmp://192.168.0.1:1935/stream/test
        返回值
        -------
        stream
            返回流媒体类Media,外面需要判空来确定是否打开成功
        """
        stream = MediaFactory.create_media(stream_type, stream_id, uri, listener)
        if stream is None:
            log.error("open stream_id[{}] error total[{}] uri is [{}] type=[{}]".format(
                stream_id, len(self.dict_streams), uri, stream_type))
            return None
        self.dict_streams[stream_id] = stream
        stream.start()
        log.info("open stream_id[{}] success total[{}] uri is [{}] type=[{}]".format(
            stream_id, len(self.dict_streams), uri, stream_type))
        return stream

    def close_stream(self, stream_id):
        """ 关闭开流媒体
        关闭流媒体播放

       参数
       ----------
       stream_id : str
           媒体ID,确保唯一
       返回值
       -------
       无
       """
        stream = self.dict_streams.pop(stream_id)
        if stream is None:
            log.error("close stream_id[%s] failed total[%d]" % (stream_id, len(self.dict_streams)))
        else:
            stream.stop()
            log.info("close stream_id[%s] success total[%d]" % (stream_id, len(self.dict_streams)))


media_manager = MediaManager()
