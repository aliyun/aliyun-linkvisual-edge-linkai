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

import logging as log
import os
import shutil
import urllib
import zipfile

from linkai.utils.tools import json_post

from linkai import conf
from linkai.algo_oam.algo_event import AlgorithmModelDeployResultEvent, AlgorithmEventErrorCodes, \
    AlgorithmDeployEventType, AlgorithmTaskResultEvent, AlgorithmTaskEventType

dict_cloud_task_id_algo_id = {}


def schedule_hook(a, b, c):
    """
    a:已经下载的数据块
    b:数据块的大小
    c:远程文件的大小
    """
    per = 100.0 * a * b / c
    if per >= 100:
        per = 100
        print("per %.2f", per)


def download_model(identifier, request_id, params):
    """
    :param identifier:
    :param request_id:
    :param params:
    :return:
    """
    log.info("download_model params:%s" % params)
    response = AlgorithmModelDeployResultEvent(AlgorithmEventErrorCodes.ALGO_EVENT_SUCCESS,
                                               AlgorithmDeployEventType.ALGO_DEPLOY_ALGO_MODEL)

    if "AlgoURL" not in params.keys() or "AlgoID" not in params.keys():
        response.Result = AlgorithmEventErrorCodes.ALGO_EVENT_PARAM_ERR
        return response.to_json()

    url = params["AlgoURL"]
    algo_id = params["AlgoID"]
    response.AlgoID = algo_id

    module_path = conf.get_string("Default", "algoModuleDir")
    algo_path = module_path + "/" + algo_id + "/"
    if os.path.isdir(algo_path) is False:
        os.mkdir(algo_path)
    algo_name = os.path.join(module_path, "temp_" + algo_id)
    try:
        urllib.request.urlretrieve(url, algo_name, schedule_hook)

        file_zip = zipfile.ZipFile(algo_name, 'r')
        for file in file_zip.namelist():
            file_zip.extract(file, algo_path)
        file_zip.close()
        os.remove(algo_name)
    except Exception as e:
        response.Result = AlgorithmEventErrorCodes.ALGO_EVENT_DOWNLOAD_ERR
        if os.path.exists(algo_name):
            os.remove(algo_name)
        return response.to_json()

    return response.to_json()


def start_algorithm_task(identifier, request_id, params):
    response = AlgorithmTaskResultEvent(AlgorithmEventErrorCodes.ALGO_EVENT_SUCCESS,
                                        AlgorithmTaskEventType.ALGO_START_ALGO_MEDEL)

    if "VideoURL" not in params.keys() or "AlgoID" not in params.keys() or "TaskID" not in params.keys():
        response.Result = AlgorithmEventErrorCodes.ALGO_EVENT_PARAM_ERR
        return response.to_json()

    video_url = params["VideoURL"]
    algorithm_name = params["AlgoID"]
    task_id = params["TaskID"]
    response.AlgoID = algorithm_name
    response.TaskID = task_id
    start_task_url = "http://127.0.0.1:11005/vision/edge/aibiz/algorithm/start"
    request = dict()
    request['algorithm'] = algorithm_name
    request['videoUrl'] = video_url
    request['taskId'] = task_id

    try:
        response = json_post(start_task_url, request)
        reply = dict()
        reply["TaskID"] = response["taskId"]
        reply["Result"] = response["result"]
        dict_cloud_task_id_algo_id[task_id] = params["AlgoID"]
        return response.to_json()

    except Exception as ex:
        response.Result = AlgorithmEventErrorCodes.ALGO_EVENT_RESPONSE_DICT_ERR
        log.error(ex)
        return response.to_json()


def stop_algorithm_task(identifier, request_id, params):
    response = AlgorithmTaskResultEvent(AlgorithmEventErrorCodes.ALGO_EVENT_SUCCESS,
                                        AlgorithmTaskEventType.ALGO_STOP_ALGO_MODEL)

    if "TaskID" not in params.keys():
        response.Result = AlgorithmEventErrorCodes.ALGO_EVENT_PARAM_ERR
        return response.to_json()

    task_id = params["TaskID"]
    response.TaskID = task_id
    if task_id not in dict_cloud_task_id_algo_id.keys():
        response.Result = AlgorithmEventErrorCodes.ALGO_EVENT_INVALID_TASK_ID_ERR
        return response.to_json()

    response.AlgoID = dict_cloud_task_id_algo_id[task_id]
    request = dict()
    request['taskId'] = task_id
    stop_task_url = "http://127.0.0.1:11005/vision/edge/aibiz/algorithm/stop"
    try:
        response = json_post(stop_task_url, request)
        reply = dict()
        reply["Result"] = response["result"]
        dict_cloud_task_id_algo_id.pop(task_id)

        return response.to_json()

    except Exception as ex:
        response.Result = AlgorithmEventErrorCodes.ALGO_EVENT_RESPONSE_DICT_ERR
        log.error(ex)
        return response.to_json()


def delete_algorithm_model(identifier, request_id, params):
    response = AlgorithmModelDeployResultEvent(AlgorithmEventErrorCodes.ALGO_EVENT_SUCCESS,
                                               AlgorithmDeployEventType.ALGO_DELETE_ALGO_MODEL)

    if "AlgoID" not in params.keys():
        response.Result = AlgorithmEventErrorCodes.ALGO_EVENT_PARAM_ERR
        return response.to_json()

    algo_id = params["AlgoID"]
    """判断该algo_id是否有任务在运行"""
    response.AlgoID = algo_id
    if algo_id in dict_cloud_task_id_algo_id.values():
        response.Result = AlgorithmEventErrorCodes.ALGO_EVENT_DELETE_ERR
        return response.to_json()

    module_path = conf.get_string("Default", "algoModuleDir")
    algo_path = module_path + "/" + algo_id + "/"
    if os.path.exists(algo_path):
        shutil.rmtree(algo_path)
    else:
        response.Result = AlgorithmEventErrorCodes.ALGO_EVENT_INVALID_ALGO_ID_ERR

        return response.to_json()

    return response.to_json()


def query_algo_task_list(identifier, request_id, params):
    pass


def query_algo_model_list():
    module_path = conf.get_string("Default", "algoModuleDir")
    return os.listdir(module_path)


def thing_call_service(identifier, request_id, params):
    log.info("thing_call_service identifier:%s, request id:%s, params:%s" %
             (identifier, request_id, params))

    if identifier == "AddAlgorithmModel":
        return download_model(identifier, request_id, params)

    elif identifier == "StartAlgorithmTask":
        return start_algorithm_task(identifier, request_id, params)

    elif identifier == "StopAlgorithmTask":
        return stop_algorithm_task(identifier, request_id, params)

    elif identifier == "DeleteAlgorithmModel":
        return delete_algorithm_model(identifier, request_id, params)

    elif identifier == "QueryAlgoTaskList":
        return query_algo_task_list(identifier, request_id, params)

    else:
        return {}
