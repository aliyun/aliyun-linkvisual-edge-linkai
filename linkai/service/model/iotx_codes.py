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

class IoTxCode(object):
    """
      IoTx code struct
      """

    def __init__(self, code, message):
        self.code = code
        self.message = message


class IoTxCodes(object):
    """
    IoTx common codes
    """

    SUCCESS_CODE = 0
    # success code
    SUCCESS = IoTxCode(SUCCESS_CODE, "success")

    # 开启任务接口
    # 算法不支持
    ALGORITHM_NOT_SUPPORT = IoTxCode(1, "algorithm not support code")

    # 资源不足
    NOT_ENOUGH_RESOURCE = IoTxCode(2, "not enough resource")

    # 设备异常
    DEVICE_EXCEPTION = IoTxCode(3, "device exception")

    # 停止任务接口
    # 任务号错误
    NOT_FIND_TASK_ID = IoTxCode(1, "not find task id")

    # 图片推理接口
    # 算法不支持
    # ALGORITHM_NOT_SUPPORT = IoTxCode(1, "algorithm not support code")

    # 获取图片失败
    GET_IMAGE_FAILED = IoTxCode(2, "get image failed")

    # 算法运行失败
    ALGORITHM_RUN_ERROR = IoTxCode(3, "algorithm run error")

    # 更新算法参数接口
    # 任务号错误
    # NOT_FIND_TASK_ID = IoTxCode(1, "not find task id")
    # API not support
    API_NOT_SUPPORT = IoTxCode(2, "api not support code")

    # 通用错误码

    # request error
    REQUEST_ERROR = IoTxCode(400, "request error.")

    # request auth error
    REQUEST_AUTH_ERROR = IoTxCode(401, "request auth error.")

    # request forbidden
    REQUEST_FORBIDDEN = IoTxCode(403, "request forbidden.")

    # request service not found
    REQUEST_SERVICE_NOT_FOUND = IoTxCode(404, "service not found.")

    # request high frequent
    REQUEST_HIGH_FREQUENT = IoTxCode(429, "too many requests.")

    # request param error
    REQUEST_PARAM_ERROR = IoTxCode(460, "request parameter error.")

    # bad username or password
    REQUEST_BAD_USERNAME_OR_PASSWORD = IoTxCode(461, "request bad username or password")

    # server error
    SERVER_ERROR = IoTxCode(500, "server error.")

    # server not available
    SERVER_NOT_AVAILABLE = IoTxCode(503, "server not available.")

    @staticmethod
    def is_success(code):
        return IoTxCodes.SUCCESS_CODE == code
