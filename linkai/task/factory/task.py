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

import datetime, threading, time, numpy, cv2
import logging
import queue

from linkai import conf
from linkai.algo_result import *
from linkai.linkkit.linkkit_adapter import on_thing_post_algo_result_event

from ..model.algorithm_event import AlgorithmEvent
from ..model.task_param import TaskStatus, TaskParamTO

log = logging.getLogger(__name__)

PIC_PATH = "static/images/"
# 人脸长宽相对增大系数，面积增大（1+ZOOM_COE）*（1+ZOOM_COE）
ZOOM_COE = 0.5


class Task(object):
    def __init__(self, task_param: "TaskParamTO"):
        # 任务参数
        self._stream_type = task_param.stream_type
        self._algo_name = task_param.algo_name
        self._id = task_param.task_id
        self._device_id = task_param.device_id
        self._video_url = task_param.video_url
        self._record = task_param.record
        self._task_status = TaskStatus.unexecuted
        self._algo_param = task_param.algo_param
        self.record_file_name = None
        self._algo_bean = None
        self._algo_info = None
        self._frame_rate = 25
        # video(断线重连线程)
        self.video_thread = threading.Thread(target=self.run)
        self.open_video_status = False
        self.open_video_exit_flag = False
        # 获取HTTP POST发送标志,  1 post , other value don't post jpg to server
        self.http_post_flag = conf.get_int("Default", "http_post_flag")
        # 获取是否发送原图标志,  1 post , other value don't post jpg to server
        self.http_post_origin_pic_flag = conf.get_int("Default", "http_post_origin_pic_flag")
        # 获取http post 方式： 1：一个request一张图片，其他值一个request多张图片
        self.http_post_method_flag = conf.get_int("Default", "http_post_method_flag")
        self.event_queue = queue.Queue(100)
        self.event_thread = threading.Thread(target=Task.run, args=(self,))

    def __del__(self):
        pass

    def run(self):
        """任务线程,每次取出队列中的一个任务进行执行"""
        while True:
            if not self.event_queue.empty():
                event = self.event_queue.get()
                on_thing_post_algo_result_event(event)
            else:
                time.sleep(0.1)

    def start(self):
        self.video_thread.start()

    def stop(self):
        self.open_video_exit_flag = True

    def run(self):
        while not self.open_video_exit_flag:
            if not self.open_video_status:
                if len(self._video_url) > 0:
                    self.set_status(TaskStatus.running)
                    self.set_open_status(True)
                    if not self.open_video():
                        self.set_status(TaskStatus.exception)
                        self.set_open_status(False)
            time.sleep(3)
        self.close_video()

    # 第三方算法需要重写这个函数
    def open_video(self):
        return True

    # 第三方算法需要重写这个函数
    def close_video(self):
        return True

    # 第三方算法实现，主要实现更新算法参数
    def update_algo_param(self, algo_param):
        log.info("task={} update_algo_param param={} ok".format(self._id, algo_param))
        return True

    # 三方算法(内部算法)结果回调
    def msg_call_back(self, pic_filename, capture_time, result: 'IoTxAlgorithmResult', oss_file_url):
        if result.code != IoTxAlgorithmCodes.SUCCESS_CODE:
            return
        for i in range(len(result.data)):
            event = result.data[i]
            algo_event = AlgorithmEvent(self._device_id, capture_time, pic_filename,
                                        self._algo_name, event, oss_file_url)
            self.event_queue.put(algo_event.to_json())

    # 内部算法需要实现
    def on_frame_h264(self, data, height, width, format_type, raw_type):
        pass

    # 内部算法需要实现
    def on_frame_cpu(self, array, height, width, format_type, raw_type, pts, dts, duration):
        pass

    # 内部算法需要实现 nvdia gpu
    def on_frame_gpu(self, data, height, width, format_type, raw_type, pts, dts, duration):
        pass

    def on_error(self, media, bus, msg):
        self.set_open_status(False)

    def on_eos(self, media, bus, msg):
        self.set_status(TaskStatus.over)
        pass

    def get_algo_name(self):
        return self._algo_name

    def get_algo_bean(self):
        return self._algo_bean

    def get_device_id(self):
        return self._device_id

    def get_task_id(self):
        return self._id

    def get_video_url(self):
        return self._video_url

    def get_record(self):
        return self._record

    def get_status(self):
        return self._task_status

    def set_status(self, task_status: "TaskStatus"):
        self._task_status = task_status

    def get_framerate(self):
        return self._frame_rate

    def set_framerate(self, framerate: "int"):
        self._frame_rate = framerate

    def get_algo_param(self):
        return self._algo_param

    def set_algo_param(self, algo_param):
        self._algo_param = algo_param

    def set_open_status(self, open_status: 'bool'):
        self.open_video_status = open_status
