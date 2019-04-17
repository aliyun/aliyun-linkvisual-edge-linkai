#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/1/9 下午8:12
# @Author  : jhon.zh
# @File    : update_algorithm.py
from .base import BaseResponse, BaseRequest
from .iotx_codes import *


class UpdateAlgorithmRequest(BaseRequest):
    """ 更新算法任务参数
    更新算法任务参数接口，请求
    """

    def __init__(self):
        self.taskId = None
        self.algoParam = None

    def check_params(self):
        if self.taskId is None:
            return False
        if self.algoParam is None:
            return False
        return True


class UpdateAlgorithmResponse(BaseResponse):
    """ 更新算法任务参数
       更新算法任务参数，回复
       """

    def __init__(self, iotx_code: 'IoTxCode' = IoTxCodes.SUCCESS):
        BaseResponse.__init__(self, iotx_code)
