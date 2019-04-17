# -*- coding: UTF-8 -*-
from enum import Enum
import json


# todo 0 未分配，1. 未运行 2.运行异常 3.运行中 4.运行结束 5. 算法不支持 6. 未打开视频 7. 解码失败
# 1. 未分配 2. 未运行  3. 运行中 4. 运行异常  5. 正常结束  6. 视频源异常
class TaskStatus(Enum):
    unallocated = 1
    unexecuted = 2
    running = 3
    exception = 4
    over = 5
    not_supported = 6


# TO(Transfer Object) ，数据传输对象, 在应用程序不同 tie( 关系 ) 之间传输的对象
class TaskParamTO(object):
    """
    任务详情

    """

    def __init__(self, task_id, device_id, video_url, algo_name, algo_param=None, record=False):
        self.task_id = task_id
        self.device_id = device_id
        self.video_url = video_url
        self.algo_name = algo_name
        self.algo_param = algo_param
        self.record = record
        self.stream_type = 'cpu'

    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__)
