# -*- coding: UTF-8 -*-

import cv2
import urllib
import numpy
import logging
import time

# from turbojpeg import TurboJPEG, TJPF_GRAY, TJSAMP_GRAY, TJPF_RGB

log = logging.getLogger(__name__)


# jpeg = TurboJPEG()


# 类定义
class ImageInfo:
    array = []
    height = 0
    width = 0
    format_type = "RGB"
    raw_type = "RGB"

    # 定义构造方法
    def __init__(self, array, height, width, format_type, raw_type):
        self.array = array
        self.height = height
        self.weight = width
        self.format_type = format_type
        self.raw_type = raw_type


# 计算时间函数
def print_run_time(func):
    def wrapper(*args, **kw):
        local_time = time.time()
        res = func(*args, **kw)
        log.info("Function={} args={} cost={}".format(func.__name__, args, 1000 * (time.time() - local_time)))
        return res

    return wrapper


@print_run_time
def get_image_info(image_type, image_data):
    try:
        raw_type = "jpeg/x-raw"
        if image_type == "url":
            resp = urllib.request.urlopen(image_data)
            image = numpy.asarray(bytearray(resp.read()), dtype="uint8")
            img = cv2.imdecode(image, cv2.IMREAD_COLOR)
            img_rgb = img[:, :, (2, 1, 0)]
        elif image_type == "local":
            img = cv2.imread(image_data)
            img_rgb = img[:, :, (2, 1, 0)]
        elif image_type == "local-gpu":
            img_rgb = None
            raw_type = "filename"
        else:
            log.error("get_image_info can not find image_type={image_type}".format(image_type))
            return None
        if img_rgb is not None:
            h, w, _ = img_rgb.shape
            image_info = ImageInfo(img_rgb, h, w, "RGB", raw_type)
        else:
            image_info = ImageInfo(image_data, 0, 0, "RGB", raw_type)
    except Exception as e:
        log.error("get_image_info error={}".format(e))
        image_info = None
    return image_info
