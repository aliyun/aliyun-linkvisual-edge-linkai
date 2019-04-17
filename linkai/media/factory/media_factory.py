# -*- coding: UTF-8 -*-#
from .media_cpu import MediaCpu
from .media_v4l2 import MediaV4L2
from .media_gpu import MediaGpu


class MediaFactory(object):
    @staticmethod
    def create_media(typ, stream_id, uri, listener):
        if uri == "local":
            typ = 'v4l2'
        map_ = {
            'cpu': MediaCpu(stream_id, uri, listener),
            'v4l2': MediaV4L2(stream_id, uri, listener),
            'gpu': MediaGpu(stream_id, uri, listener),
        }
        return map_[typ]
