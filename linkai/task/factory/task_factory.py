# -*- coding: UTF-8 -*-#
from .common_task import CommonTask

from ..model.task_param import TaskParamTO


class TaskFactory(object):
    @staticmethod
    def create_task(task_param: "TaskParamTO"):
        return CommonTask(task_param)
