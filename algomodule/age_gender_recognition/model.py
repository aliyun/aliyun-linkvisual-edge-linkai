#
# # encoding: utf-8
#
import sys
import time

from inference_engine import IENetwork, IEPlugin
import os
import logging
import cv2
import platform
from algo_result import IoTxAlgorithmResult, IoTxAgeGenderRecognitionEvent, IoTxAlgorithmCodes, IoTxAlgorithmCode


log = logging.getLogger(__name__)
print(__name__)

model_path = os.path.dirname(__file__)
plugin_dirs = os.environ['OPENVINO_PLUGIN_DIR']

# detection_graph = tf.Graph()
exec_net = None
input_blob = None
output_blob = None


# 计算时间函数
def print_run_time(func):
    def wrapper(*args, **kw):
        local_time = time.time()
        res = func(*args, **kw)
        # log.info("Function [%s] cost %.4fms %s" % (func.__name__, 1000 * (time.time() - local_time), args[0]))
        return res
    return wrapper


def register():
    """
    注册函数会在首次加载算法模块时调用
    需要返回算法的描述信息, 和创建算法对象的方法
    算法对象必须包含image_inference函数
    :return: 算法描述信息
    """

    init_model()

    info = {
        "name": __name__,
        "version": "1.0.0",
        "author": "WideZhang",
        "desc":
            '''
            年龄和性别识别
            '''
    }
    return info


def init_model():
    # 初始化
    global exec_net, input_blob, output_blob
    model_xml = model_path + "/age-gender-recognition-retail-0013.xml"
    model_bin = os.path.splitext(model_xml)[0] + ".bin"
    device = 'CPU'  # Specify the target device to infer on; CPU, GPU, FPGA or MYRIAD is acceptable.
    if os.environ.get("OPENVINO_DEVICE") == "GPU":
        device = "GPU"
    # Plugin initialization for specified device and load extensions library if specified
    plugin = IEPlugin(device=device, plugin_dirs=plugin_dirs)
    osName = platform.system()
    if (osName == 'Linux'):
        plugin.add_cpu_extension(plugin_dirs + "/libcpu_extension_avx2.so")
    elif (osName == 'Darwin'):
        plugin.add_cpu_extension(plugin_dirs + "/libcpu_extension.dylib")
    # Read IR
    # log.info("Loading network files:\n\t{}\n\t{}".format(model_xml, model_bin))
    net = IENetwork.from_ir(model=model_xml, weights=model_bin)

    if "CPU" in plugin.device:
        supported_layers = plugin.get_supported_layers(net)
        not_supported_layers = [l for l in net.layers.keys() if l not in supported_layers]
        if len(not_supported_layers) != 0:
            log.error("Following layers are not supported by the plugin for specified device {}:\n {}".
                      format(plugin.device, ', '.join(not_supported_layers)))
            log.error("Please try to specify cpu extensions library path in sample's command line parameters using -l "
                      "or --cpu_extension command line argument")
            sys.exit(1)

    log.info("Preparing input blobs")
    input_blob = next(iter(net.inputs.items()))
    output_blob = next(iter(net.outputs))

    exec_net = plugin.load(network=net)
    print(net.inputs)
    print(net.outputs)
    del net


class Model:
    """
        此类的名称不要修改
        框架会调用 .Model() 创建实例
        每个实例对应一个tensor session
    """

    @print_run_time
    def image_inference(self, array, height, width, format_type, raw_type):
        """
        图像推理函数
        :param array:   ndarray 一维结构
        :return: 返回结构体
        """
        if format_type == "RGBA":
            imagesrc = array[:, :, :, 0:3]
        elif format_type != "RGB":
            log.error("Not support {}".format(format_type))
        else:
            """RGB转BGR"""
            imagesrc = array[:, :, (2, 1, 0)]

        blob_name, rect_shape = input_blob
        n, c, h, w = rect_shape
        if format_type == "RGBA":
            image = cv2.resize(imagesrc[0], (w, h))  # RGBA
        else:
            image = cv2.resize(imagesrc, (w, h))  # RGB
        image = image.transpose((2, 0, 1))

        image = image.reshape((n, c, h, w))
        res = exec_net.infer(inputs={blob_name: image})
        flag = False
        result = IoTxAlgorithmResult(IoTxAlgorithmCodes.SUCCESS)
        if "age_conv3" in res.keys() and "prob" in res.keys():
            flag = True
            event = IoTxAgeGenderRecognitionEvent()
            event.age = res["age_conv3"][0][0][0]*100
            event.age = float(event.age[0])
            event.gender = res["prob"][0][0][0]
            gender = "male"
            if event.gender >= 0.5:
                event.gender = "female"

            log.info("age = {}, gender = {}".format(event.age, gender))
            result.append(event)
        if flag is True:
            return result
        else:
            return IoTxAlgorithmResult(IoTxAlgorithmCodes.ALGORITHM_NO_FACE)

