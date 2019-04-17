# -*- coding: UTF-8 -*-

import logging
import time
import threading
import queue
from linkai import conf
from .factory.task_factory import TaskFactory
from .model.task_param import TaskParamTO

log = logging.getLogger(__name__)
PIC_PATH = "static/images/"
MAX_PIC_NUM = conf.get_int("OSS_CFG", "max_pic_number")


class TaskManager(object):
    """ 任务管理，单件实例task_manager

    对基类为Task的任务类进行管理
    Attributes:
        dict_tasks: 任务集合MAP（所有任务）
        task_thread: 任务管理线程，不堵住主线程而另外启动的线程，让任务可以异步执行
        task_queue:  异步还需要处理的任务队列（待执行任务）
        task_thread_exit_flag: 任务处理线程退出，目前不会退出。
    """

    def __init__(self):
        # 任务线程，为了不卡网络线程，单独启动线程运行task
        self.task_thread = threading.Thread(target=TaskManager.run, args=(self,))
        self.task_thread_exit_flag = False
        self.dict_tasks = {}
        self.dict_tasks_mutex = threading.Lock()
        self.task_queue = queue.Queue(100)
        self.task_thread.start()
        pass

    def run(self):
        """任务线程,每次取出队列中的一个任务进行执行"""
        while not self.task_thread_exit_flag:
            if not self.task_queue.empty():
                task_bean = self.task_queue.get()
                task_bean.start()
            else:
                time.sleep(0.1)

    def get_task_by_id(self, task_id):
        task_bean = None
        self.dict_tasks_mutex.acquire()
        if task_id in self.dict_tasks.keys():
            task_bean = self.dict_tasks[task_id]
        self.dict_tasks_mutex.release()
        return task_bean

    def pop_task_by_id(self, task_id):
        task_bean = None
        self.dict_tasks_mutex.acquire()
        if task_id in self.dict_tasks.keys():
            task_bean = self.dict_tasks.pop(task_id)
        self.dict_tasks_mutex.release()
        return task_bean

    def start_algo_task(self, task_param: "TaskParamTO"):
        """启动一个算法任务，通过任务工厂创建任务，然后启动任务"""
        task_bean = self.get_task_by_id(task_param.task_id)
        if task_bean is not None:
            log.error("start_algo_task err, task_id={} is exist".format(task_param.task_id))
            return False
        task_bean = TaskFactory.create_task(task_param)
        self.dict_tasks_mutex.acquire()
        self.dict_tasks[task_param.task_id] = task_bean
        self.dict_tasks_mutex.release()
        self.task_queue.put(task_bean)
        log.info("start_algo_task param={}".format(task_param.to_json()))
        return True

    def stop_algo_task(self, task_id):
        """关闭一个算法任务"""
        task_bean = self.pop_task_by_id(task_id)
        if task_bean is None:
            log.error("stop task_id={} failed total={}".format(task_id, len(self.dict_tasks)))
            return False
        task_bean.stop()
        log.info("stop task_id={} success total={}".format(task_id, len(self.dict_tasks)))
        return True

    def update_algo_task(self, task_id, algo_param):
        task_bean = self.get_task_by_id(task_id)
        if task_bean is None:
            return False
        return task_bean.update_algo_param(algo_param)

    def get_all_algo_tasks(self):
        """获取所有算法任务"""
        return self.dict_tasks

    def get_algo_task(self, task_id):
        """获取某个task_id的任务"""
        if task_id in self.dict_tasks.keys():
            return self.dict_tasks[task_id]
        return None


task_manager = TaskManager()
