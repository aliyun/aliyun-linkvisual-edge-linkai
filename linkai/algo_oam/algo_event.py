# -*- coding: utf-8 -*-
import json
from enum import Enum


class AlgorithmDeployEventType(Enum):
    ALGO_DELETE_ALGO_MODEL = 0
    ALGO_DEPLOY_ALGO_MODEL = 1


class AlgorithmTaskEventType(Enum):
    ALGO_STOP_ALGO_MODEL = 0
    ALGO_START_ALGO_MEDEL = 1


class AlgorithmEventErrorCodes(object):
    """
    Algorithm  event error codes
    """

    ALGO_EVENT_SUCCESS = "Success"
    ALGO_EVENT_PARAM_ERR = "Input param error"
    ALGO_EVENT_DELETE_ERR = "Delete failed because of algo task running"
    ALGO_EVENT_DOWNLOAD_ERR = "Download algo model failed"
    ALGO_EVENT_RESPONSE_DICT_ERR = "Response key error after starting task"
    ALGO_EVENT_INVALID_ALGO_ID_ERR = "The algo id does not exist"
    ALGO_EVENT_INVALID_TASK_ID_ERR = "The task id does not exist"


class AlgorithmModelDeployResultEvent(object):
    """
    Algorithm deploy result event
    0 represents DeleteAlgorithmModel, 1 represents AddAlgorithmModel
    """
    def __init__(self, result: "AlgorithmEventErrorCodes", deply_type: "AlgorithmDeployEventType"):
        self.Result = result
        self.DeployType = deply_type.value
        self.AlgoID = ""

    def to_json(self):
        return self.__dict__


class AlgorithmTaskResultEvent(object):
    """
    Algorithm tast result event
    0 represents StopAlgorithmTask, 1 represents StartAlgorithmTask
    """
    def __init__(self, result: "AlgorithmEventErrorCodes", task_type: "AlgorithmTaskEventType"):
        self.Result = result
        self.TaskType = task_type.value
        self.AlgoID = ""
        self.TaskID = ""

    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__)
