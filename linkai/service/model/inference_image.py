# -*- coding: UTF-8 -*-
from .base import BaseResponse, BaseRequest
from .iotx_codes import *
from ...algo_result import IoTxAlgorithmEvent


class InferenceRequest(BaseRequest):
    """ 图片推理
    图片推理接口，请求
    """

    def __init__(self):
        self.data = None
        self.algorithm = None
        self.type = "local"

    def check_params(self):
        if self.data is None:
            return False
        if self.algorithm is None:
            return False
        return True


class InferenceResponse(BaseResponse):
    """ 图片推理
       图片推理接口，回复
       """

    def __init__(self, iotx_code: 'IoTxCode' = IoTxCodes.SUCCESS, algorithm_code=0, algorithm_message=""):
        BaseResponse.__init__(self, iotx_code)
        self.algorithm_code = algorithm_code
        self.algorithm_message = algorithm_message
        self.data = []

    def append(self, algo_event: 'IoTxAlgorithmEvent'):
        self.data.append(algo_event)
