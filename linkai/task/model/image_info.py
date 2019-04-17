# -*- coding: UTF-8 -*-
class ImageInfo(object):
    def __init__(self, array, height, width, format_type, raw_type):
        self.array = array
        self.height = height
        self.width = width
        self.format_type = format_type
        self.raw_type = raw_type
