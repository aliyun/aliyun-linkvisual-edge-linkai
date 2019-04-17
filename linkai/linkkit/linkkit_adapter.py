import queue
import shutil
import threading
import time

import linkai.linkkit.linkkit as linkkit
from linkai import conf
import os
import urllib
import zipfile
import logging as log
from concurrent.futures import ThreadPoolExecutor

from linkai.algo_oam.algo_event import AlgorithmModelDeployResultEvent, AlgorithmEventErrorCodes, \
    AlgorithmDeployEventType, AlgorithmTaskResultEvent, AlgorithmTaskEventType
from linkai.algo_oam.algo_oam import thing_call_service, query_algo_model_list
from linkai.utils.tools import json_post

executor = ThreadPoolExecutor(max_workers = 1)
host_name = conf.get_string("LinkKit", "host_name")
if "PRODUCT_KEY" in os.environ:
    product_key = os.environ["PRODUCT_KEY"]
else:
    product_key = conf.get_string("LinkKit", "product_key")
log.info("product_key={}".format(product_key))

if "DEVICE_NAME" in os.environ:
    device_name = os.environ["DEVICE_NAME"]
else:
    device_name = conf.get_string("LinkKit", "device_name")
log.info("device_name={}".format(device_name))

if "DEVICE_SECRET" in os.environ:
    device_secret = os.environ["DEVICE_SECRET"]
else:
    device_secret = conf.get_string("LinkKit", "device_secret")
log.info("device_secret={}".format(device_secret))

platform = conf.get_string("LinkKit", "platform")
lk = linkkit.LinkKit(host_name, product_key, device_name, device_secret)
lk.enable_logger(0)
lk.thing_setup("model.json")
"""算法模型列表"""
list_algo_id = []
"""云端的taskid和算法算法的algoid的映射字典"""
dict_cloud_task_id_algo_id = {}
"""云端的taskid和算法启动分配的taskid的映射字典"""
dict_cloud_taskid_algo_taskid = {}
service_queue = queue.Queue(10)


class ServiceMsg(object):
    def __init__(self, identifier, request_id, params):
        self.identifier = identifier
        self.request_id = request_id
        self.params = params


def run():
    """任务线程,每次取出队列中的一个任务进行执行"""
    while True:
        if not service_queue.empty():
            service_msg = service_queue.get()
            result = thing_call_service(service_msg.identifier, service_msg.request_id, service_msg.params)
            if service_msg.identifier == "AddAlgorithmModel":
                download_model_response(result)

            elif service_msg.identifier == "StartAlgorithmTask":
                start_algorithm_task_response(result)

            elif service_msg.identifier == "StopAlgorithmTask":
                stop_algorithm_task_response(result)

            elif service_msg.identifier == "DeleteAlgorithmModel":
                delete_algorithm_model_response(result)

            elif service_msg.identifier == "QueryAlgoTaskList":
                query_algo_task_list_respnse(result)

            else:
                time.sleep(0.1)


def on_connect(session_flag, rc, userdata):
    print("on_connect:%d,rc:%d,userdata:" % (session_flag, rc))
    pass


def on_disconnect(rc, userdata):
    print("on_disconnect:rc:%d,userdata:" % rc)


def download_model_response(result):
    """
    :param result: 下发算法模型的结果
    :return: None
    """

    identifier = "AlgorithmModelDeployResult"

    on_thing_post_algo_property(query_algo_model_list())

    lk.thing_trigger_event((identifier, result))


def start_algorithm_task_response(result):
    """
    :param result: 开启算法任务的结果
    :return: None
    """

    identifier = "AlgorithmTaskResult"

    lk.thing_trigger_event((identifier, result))


def stop_algorithm_task_response(result):
    """
    :param result: 停止算法任务的结果
    :return: None
    """
    identifier = "AlgorithmTaskResult"

    lk.thing_trigger_event((identifier, result))


def delete_algorithm_model_response(result):
    """
    :param result: 删除算法模型的结果
    :return: None
    """
    identifier = "AlgorithmModelDeployResult"

    on_thing_post_algo_property(query_algo_model_list())

    lk.thing_trigger_event((identifier, result))


def query_algo_task_list_respnse(result):
    """
    :param result:
    :return:
    """
    pass


def on_thing_call_service(identifier, request_id, params, userdata):
    """
    :param identifier: 服务标识符
    :param request_id: 请求id
    :param params: 输入参数
    :param userdata: 用户数据
    :return: None
    """
    # lk.thing_answer_service(identifier, request_id, 400)
    print("on_thing_call_service identifier:%s, request id:%s, params:%s" %
          (identifier, request_id, params))
    service_msg = ServiceMsg(identifier, request_id, params)
    service_queue.put(service_msg)


def on_thing_post_algo_result_event(event):
    """
    :param event: 上报的事件
    :return: None
    """
    identifier = "AlgorithmTaskResult"
    url = event["url"]
    algo_id = event["algo_id"]
    result = event["value"]
    param = dict()
    param["AlgoID"] = algo_id
    param["Result"] = result
    param["PicURL"] = url
    lk.thing_trigger_event((identifier, param))


def on_thing_enable(userdata):
    log.info("on_thing_enable")
    prop_data = {
        "UploadPlatform": platform,
    }
    # 平台属性上报
    rc, request_id = lk.thing_post_property(prop_data)
    log.info("thing_post_property rc = {} request_id = {}".format(rc, request_id))

    on_thing_post_algo_property(query_algo_model_list())


def on_thing_post_algo_property(algo_list):
    """
    :param algo_list: 算法模型列表
    :return:
    """
    prop_data = {
        "AlgorithmModelList": str(algo_list),
    }
    # 平台属性上报
    rc, request_id = lk.thing_post_property(prop_data)
    log.info("thing_post_property rc = {} request_id = {}".format(rc, request_id))


# 属性上报回调
def on_thing_prop_post(request_id, code, data, message, userdata):
    log.info("on_thing_prop_post request id:{}, code:{}, data:{} message:{}".format(request_id,
                                                                                    code,
                                                                                    str(data),
                                                                                    message))


def on_thing_event_post(event, request_id, code, data, reply_message, user_data):
    log.info("on_thing_event_post event: {} request_id:{}, code:{}, data:{}, reply_message:{}".format(event,
                                                                                                      request_id,
                                                                                                      code,
                                                                                                      str(data),
                                                                                                      reply_message))


lk.on_connect = on_connect
lk.on_disconnect = on_disconnect
lk.on_thing_call_service = on_thing_call_service
lk.on_thing_enable = on_thing_enable
lk.on_thing_prop_post = on_thing_prop_post
lk.on_thing_event_post = on_thing_event_post
lk.connect_async()
threading.Thread(target=run, args=()).start()
