# -*- coding: UTF-8 -*-
import socket, time, uuid, os, logging
from flask import Flask, request, jsonify, g, Response
from linkai.service.model.query_task import QueryTaskRequest, QueryTaskResponse, TaskDTO

from linkai.algostore import algo_manager
from linkai.utils import image
from linkai.task.model.task_param import TaskParamTO
from linkai.task.manager import task_manager
from linkai.algo_result import *
from .model.start_algorithm import StartAlgorithmRequest, StartAlgorithmResponse
from .model.stop_algorithm import StopAlgorithmResponse, StopAlgorithmRequest
from .model.inference_image import InferenceRequest, InferenceResponse
from .model.base import BaseResponse
from .model.iotx_codes import IoTxCodes

log = logging.getLogger(__name__)

pwd = os.getcwd()


class MyResponse(Response):
    @classmethod
    def force_type(cls, response: "BaseResponse", environ=None):
        response = json.loads(response.to_json())
        response = jsonify(response)
        return super(Response, cls).force_type(response, environ)


app = Flask(__name__, static_folder=pwd + '/static', template_folder=pwd + '/templates')
app.response_class = MyResponse


@app.before_first_request
def before_first_request():
    log.debug("before_first_request")


@app.before_request
def before_request():
    g.time = time.time()


@app.after_request
def after_request(response):
    if request.path.find("static") == -1 and request.method == "POST":
        trace_id = request.headers.get("Trace_ID")
        cost_time = 1000 * (time.time() - g.time)
        req = str(request.get_data(), 'utf-8').replace('\r', '').replace('\n', '').replace('\t', '')
        log.info(
            "req_url={url} req_body={req} resp={resp} trace_id={trace_id} cost_time={time}ms".format(url=request.path,
                                                                                                     req=req,
                                                                                                     resp=str(
                                                                                                         response.data,
                                                                                                         'utf-8'),
                                                                                                     trace_id=trace_id,
                                                                                                     time=cost_time))
    return response


@app.errorhandler(500)
def internal_server_error(e):
    if request.path.find("static") == -1 and request.method == "POST":
        trace_id = request.headers.get("Trace_ID")
        req = str(request.get_data(), 'utf-8').replace('\r', '').replace('\n', '').replace('\t', '')
        log.error(
            "req_url={url} req_body={req} Exception={e} trace_id={trace_id}".format(url=request.path,
                                                                                    req=req,
                                                                                    e=e,
                                                                                    trace_id=trace_id))
    return BaseResponse(IoTxCodes.SERVER_ERROR)


@app.route('/vision/edge/aibiz/algorithm/start', methods=['POST'])
def handle_start_algorithm():
    """
    开启算法任务
    :return:StartAlgorithmResponse
    """
    # "result": 0 // 0：成功 1：算法不支持 2：资源不足 3：设备异常
    req = StartAlgorithmRequest().init_from_json(request.get_data())
    if not req.check_params():
        return StartAlgorithmResponse(IoTxCodes.REQUEST_PARAM_ERROR)
    if not algo_manager.check_algorithm(req.algorithm):
        return StartAlgorithmResponse(IoTxCodes.ALGORITHM_NOT_SUPPORT)
    task_id = req.taskId
    if task_id is None:
        task_id = uuid.uuid4().hex
    task_param = TaskParamTO(task_id, req.deviceId, req.videoUrl, req.algorithm, req.algoParam)

    task_manager.start_algo_task(task_param)
    return StartAlgorithmResponse(IoTxCodes.SUCCESS, task_id)


@app.route('/vision/edge/aibiz/algorithm/stop', methods=['POST'])
def handle_stop_algorithm():
    """
    停止算法任务
    :return:StopAlgorithmResponse
    """
    req = StopAlgorithmRequest().init_from_json(request.get_data())
    if not req.check_params():
        return StopAlgorithmResponse(IoTxCodes.REQUEST_PARAM_ERROR)

    ret = task_manager.stop_algo_task(req.taskId)
    if ret is False:
        return StopAlgorithmResponse(IoTxCodes.NOT_FIND_TASK_ID)
    return StopAlgorithmResponse(IoTxCodes.SUCCESS)


@app.route('/vision/edge/aibiz/algorithm/queryTask', methods=['POST'])
def handle_query_all_task():
    """
    查询所有算法任务
    :return:QueryTaskResponse
    """
    req = QueryTaskRequest().init_from_json(request.get_data())
    resp = QueryTaskResponse(IoTxCodes.SUCCESS)
    if req.taskId is not None and len(req.taskId) > 0:

        task_bean = task_manager.get_task_by_id(req.taskId)
        if task_bean is not None:
            task_dto = TaskDTO(req.taskId, task_bean.get_device_id(), task_bean.get_video_url(),
                               task_bean.get_algo_name(),
                               task_bean.get_record(), task_bean.get_status().value, task_bean.get_algo_param())
            resp.append(task_dto)
    else:
        src_tasks = task_manager.get_all_algo_tasks()
        for taskId, task_bean in src_tasks.items():
            task_dto = TaskDTO(taskId, task_bean.get_device_id(), task_bean.get_video_url(),
                               task_bean.get_algo_name(),
                               task_bean.get_record(), task_bean.get_status().value, task_bean.get_algo_param())
            resp.append(task_dto)

    return resp


@app.route('/vision/edge/aibiz/image/inference', methods=['POST'])
def handle_inference_image():
    """
    图片推理同步接口
    :return:InferenceResponse
    """
    # "result": 0 // 0：成功 1：算法不支持 2：资源不足 3：设备异常 5: 算法运行错误
    req = InferenceRequest().init_from_json(request.get_data())
    if not req.check_params():
        return InferenceResponse(IoTxCodes.REQUEST_PARAM_ERROR)
    if not algo_manager.check_algorithm(req.algorithm):
        return InferenceResponse(IoTxCodes.ALGORITHM_NOT_SUPPORT)
    image_info = image.get_image_info(req.type, req.data)
    if image_info is None:
        return InferenceResponse(IoTxCodes.GET_IMAGE_FAILED)

    algo_bean = algo_manager.create_algorithm_with_single(req.algorithm)
    result = algo_bean.image_inference(image_info.array, image_info.height, image_info.width,
                                       image_info.format_type,
                                       image_info.raw_type)
    if result.code == IoTxAlgorithmCodes.SUCCESS_CODE:
        iotx_code = IoTxCodes.SUCCESS
    else:
        iotx_code = IoTxCodes.ALGORITHM_RUN_ERROR
    resp = InferenceResponse(iotx_code, result.code, result.desc)
    for i in range(len(result.data)):
        resp.append(result.data[i])
    return resp


@app.route('/')
def hello():
    return "Hello, World!"


