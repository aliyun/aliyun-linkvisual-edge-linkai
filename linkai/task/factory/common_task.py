# -*- coding: UTF-8 -*-
import datetime, threading, logging, time
from collections import deque
from ffmpy import FFmpeg
from linkai.algostore import algo_manager
from linkai.utils import tools
from linkai.oss.client import oss_client
from linkai.media.manager import media_manager
from linkai.algo_result import *
from linkai.utils.algorithm_base import OSDBase, OSDType, Rect
from .task import Task, PIC_PATH
from ..model.image_info import ImageInfo
from ..model.task_param import TaskStatus, TaskParamTO

log = logging.getLogger(__name__)

time_interval = 1
before_alarm_time = 10
after_alarm_time = 10


class CommonTask(Task):
    def __init__(self, task_param: "TaskParamTO"):
        super(CommonTask, self).__init__(task_param)
        # 算法处理RGBA
        self.image_info = None
        self.process_image_flag = False
        self.process_image_exit_flag = False
        self.image_thread = threading.Thread(target=self.process_frame)

    def __del__(self):
        pass

    def start(self):
        self._algo_bean = algo_manager.create_algorithm(self._algo_name, self._algo_param)
        if self._algo_bean is None:
            self.set_status(TaskStatus.not_supported)
            return
        self._algo_info = algo_manager.get_algo_info(self._algo_name)
        Task.start(self)
        self.image_thread.start()
        pass

    def stop(self):
        Task.stop(self)
        self.process_image_exit_flag = True
        pass

    # 打开视频
    def open_video(self):
        return media_manager.open_stream(self._id, self._video_url, self, self._stream_type)

    #  关闭视频
    def close_video(self):
        media_manager.close_stream(self._id)

    # 内部算法需要实现 nvdia gpu
    def on_frame_gpu(self, data, height, width, format_type, raw_type, pts, dts, duration):
        if self.process_image_flag is False:
            self.image_info = ImageInfo(data, height, width, format_type, raw_type)
            self.process_image_flag = True
        return

    def on_frame_cpu(self, array, height, width, format_type, raw_type, pts, dts, duration):
        if self.process_image_flag is False:
            self.image_info = ImageInfo(array, height, width, format_type, raw_type)
            self.process_image_flag = True
        return

    # 异步处理on_frame
    def process_frame(self):
        while not self.process_image_exit_flag:
            if self.process_image_flag is False:
                time.sleep(0.001)
                continue
            now = datetime.datetime.now()
            time_cost = int((now - self.mq_last_time).seconds)
            if time_cost < time_interval:
                time.sleep(0.001)
                continue
            self.do_algo_task(self.image_info)
            self.process_image_flag = False
        time.sleep(0.001)

    def do_algo_task(self, image_info):
        # 算法
        array = image_info.array
        height = image_info.height
        width = image_info.width
        format_type = image_info.format_type
        raw_type = image_info.raw_type
        result = self._algo_bean.image_inference(array, height, width, format_type, raw_type)
        if result.code == IoTxAlgorithmCodes.SUCCESS_CODE:
            pic_filename = "T{}_{}.jpg".format(self._id,
                                               time.strftime("%Y-%m-%d_%H:%M:%S",
                                                             time.localtime(time.time())))
            tools.compress_buf_to_jpg(format_type, width, height, array, PIC_PATH + pic_filename)
            # 定制，图片直接上传云端
            oss_client.put_object_from_file(pic_filename, PIC_PATH + pic_filename)
            oss_file_url = oss_client.generate_signed_url(pic_filename, 24*3600)
            capture_time = time.mktime(datetime.datetime.now().timetuple())
            self.msg_call_back(pic_filename, capture_time, result, oss_file_url)


