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


class OSDType(object):
    """
    OSD type codes
    """
    # 叠加矩形框
    OSD_RECT = 0

    # 叠加图片
    OSD_IMAGE = 1

    # 叠加字符信息
    OSD_STRING = 2

    # 其他
    OSD_EXTERNAL = 3


class Rect(object):
    # x,y为左上角坐标， w和h分别为矩形框的宽和高
    # 坐标位置 0～1 归一化
    def __init__(self, x, y, w, h):
        self.x = x
        self.y = y
        self.w = w
        self.h = h


class Image(object):
    def __init__(self, data, width, height, img_type):
        self.image_data = data
        self.image_width = width
        self.image_height = height
        self.image_type = img_type


class OSDBase(object):
    def __init__(self, osd_type=OSDType.OSD_RECT, rect=None, image=None, desc=None):
        self.osd_type = osd_type
        self.rect = rect
        self.image_info = image
        self.description = desc

