# -*- coding: UTF-8 -*-
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

import socket
import urllib
import json
import time
from urllib.error import URLError
import cv2
import numpy
import logging

log = logging.getLogger(__name__)


def json_post(url, req_value):
    timeout = 2
    socket.setdefaulttimeout(timeout)
    response = dict()
    try:
        req = urllib.request.Request(url)
        req.add_header('Content-Type', 'application/json')
        post_body = json.dumps(req_value).encode('utf-8')
        page = urllib.request.urlopen(req, post_body)
        res = page.read()
        page.close()
        response = json.loads(res.decode('utf-8'))
    except URLError as e:
        if hasattr(e, "reason"):
            message = "Failed to reach a server. Reason={Reason}".format(Reason=e.reason)
        else:
            message = "The server could not fulfill the request.Error code={code}".format(code=e.strerror)
        response['code'] = 500
        response['message'] = message
    except socket.error as e:
        message = "Failed to reach a server.e={e}".format(e=e.strerror)
        response['code'] = 500
        response['message'] = message
    except Exception as e:
        message = "Failed to reach a server.e={e}".format(e=e)
        response['code'] = 500
        response['message'] = message
    return response


def get_time_stamp():
    ct = time.time()
    local_time = time.localtime(ct)
    data_head = time.strftime("P%Y_%m_%d_%H_%M_%S", local_time)
    data_secs = (ct - int(ct)) * 1000
    time_stamp = "%s_%03d" % (data_head, data_secs)
    return time_stamp


# buf转jpg
def compress_buf_to_jpg(image_type, pic_width, pic_height, input_buffer, file_name):
    if file_name is None:
        return False
    str_encode = compress_buf_to_jpg_data(image_type, pic_width, pic_height, input_buffer)
    with open(file_name, 'wb+') as f:
        f.write(str_encode)
        f.close()
    return True


# buf转jpg_data
def compress_buf_to_jpg_data(image_type, pic_width, pic_height, input_buffer):
    if image_type != "RGBA" and image_type != "BGRA":
        log.error("compress_buf_to_jpg err unsupport image_type={}".format(image_type))
        return None
    np_arr = numpy.fromstring(input_buffer, numpy.uint8)
    color_image = np_arr.reshape(pic_height, pic_width, 4)
    if image_type == "RGBA":
        color_image = cv2.cvtColor(color_image, cv2.COLOR_RGBA2BGRA)
    img_encode = cv2.imencode('.jpg', color_image)[1]
    data_encode = numpy.array(img_encode)
    str_encode = data_encode.tostring()
    return str_encode
