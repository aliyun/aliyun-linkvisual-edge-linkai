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


class StopAlgorithmRequest(BaseRequest):
    """ 停止算法任务
    停止算法任务接口，请求
    """

    def __init__(self):
        self.taskId = None

    def check_params(self):
        if self.taskId is None:
            return False
        return True


class StopAlgorithmResponse(BaseResponse):
    """ 停止算法任务
       停止算法任务接口，回复
       """

    def __init__(self, iotx_code: 'IoTxCode' = IoTxCodes.SUCCESS):
        BaseResponse.__init__(self, iotx_code)
