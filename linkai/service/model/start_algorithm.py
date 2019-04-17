# -*- coding: UTF-8 -*-
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
