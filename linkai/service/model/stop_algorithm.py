# -*- coding: UTF-8 -*-
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
