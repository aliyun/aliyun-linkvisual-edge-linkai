# -*- coding: UTF-8 -*-
from .base import BaseResponse, BaseRequest
from .iotx_codes import *


class QueryTaskRequest(BaseRequest):
    """ 查询任务
    查询任务接口，请求
    """

    def __init__(self):
        self.taskId = ""


class TaskDTO(object):
    """
      任务详情

      """

    def __init__(self, task_id, device_id, video_url, algo_name, record, status, algo_param):
        self.taskId = task_id
        self.deviceId = device_id
        self.videoUrl = video_url
        self.algorithm = algo_name
        self.record = record
        self.status = status
        self.algoParam = algo_param


class QueryTaskResponse(BaseResponse):
    """ 查询任务
       查询任务接口，回复
       """

    def __init__(self, iotx_code: 'IoTxCode' = IoTxCodes.SUCCESS):
        BaseResponse.__init__(self, iotx_code)
        self.taskList = []

    def append(self, task: "TaskDTO"):
        self.taskList.append(task)
