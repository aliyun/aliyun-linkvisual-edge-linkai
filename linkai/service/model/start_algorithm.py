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

from .base import BaseResponse, BaseRequest
from .iotx_codes import *


class StartAlgorithmRequest(BaseRequest):
    """ 开启算法
    开启算法任务接口，请求
    """

    def __init__(self):
        self.algorithm = None  # 算法名
        self.deviceId = 0  # LVE里的设备Id
        self.videoUrl = ""  # 视频url,本地文件,rtmp,rtsp等,这个如果存在，deviceId就会失效
        self.algoParam = ""  # 算法参数
        self.taskId = None  # 算法运行的task_id

    def check_params(self):
        if self.algorithm is None:
            return False
        if self.deviceId == 0 and self.videoUrl is None:
            return False
        return True


class StartAlgorithmResponse(BaseResponse):
    """ 开启算法
       开启算法任务接口，回复
       """

    def __init__(self, iotx_code: 'IoTxCode' = IoTxCodes.SUCCESS, task_id=""):
        BaseResponse.__init__(self, iotx_code)
        self.taskId = task_id
