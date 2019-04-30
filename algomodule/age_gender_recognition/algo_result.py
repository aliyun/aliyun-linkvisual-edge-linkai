#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2018/12/25 上午11:03
# @Author  : jhon.zh
# @File    : algo_result.py
from enum import Enum
import json


class IoTxAlgorithmEventType(Enum):
    Undefined = 0  # 未定义
    IllegalParking = 10001  # 违章停车
    IllegalSale = 10002  # 占道经营
    BikesRecognition = 10003  # 摩托车识别
    PedestrainsRecognition = 10004  # 行人识别
    VehiclesRecognitionEvent = 10005  # 车辆识别

    FaceDetect = 20003  # 人脸检测
    HumanDetect = 20004  # 人体检测
    FaceQCheck = 60005  # 人脸质量分
    FaceRecognize = 60006  # 人脸特征提取
    ClothesCount = 60007  # 叠衣计数
    ObjectDetection = 60008  # 目标检测
    AgeGenderRecognition = 60009  # 年龄性别检测
    EmotionsRecognition = 60010  # 表情检测
    HumanPosesEstimation = 60011  # 人体姿态估计
    VehicleLicensePlateDetection = 60012  # 车辆和车牌检测
    LicensePlateRecognition = 60013  # 车牌识别


class IoTxAlgorithmCode(object):
    """
      IoTx Algorithm code struct
      """

    def __init__(self, code, message):
        self.code = code
        self.message = message


class IoTxAlgorithmCodes(object):
    """
    IoTx Algorithm  common codes
    """

    SUCCESS_CODE = 0
    # success code
    SUCCESS = IoTxAlgorithmCode(SUCCESS_CODE, "success")
    ALGORITHM_PARAM_ERROR = IoTxAlgorithmCode(460, "param error")

    # algorithm FaceQCheck
    ALGORITHM_NO_FACE = IoTxAlgorithmCode(4001, "no face")
    ALGORITHM_MULTI_FACE = IoTxAlgorithmCode(4002, "mutilface")
    ALGORITHM_SMALL_FACE = IoTxAlgorithmCode(4003, "small face")

    # algorithm HumanDetect
    ALGORITHM_NO_HUMAN = IoTxAlgorithmCode(6001, "no human")

    # algorithm ObjectDetection
    ALGORITHM_NO_OBJECT = IoTxAlgorithmCode(7001, "no object")

    # algorithm LicenseplateRecognition
    ALGORITHM_NO_LICENSE_PLATE = IoTxAlgorithmCode(8001, "no license plate was detected")

    @staticmethod
    def is_success(code):
        return IoTxAlgorithmCodes.SUCCESS_CODE == code


class IoTxAlgorithmResult(object):
    """
    算法结果
    Attributes:
        data:[IllegalParkingEvent,IllegalSaleEvent] 事件列表
        code:错误码
        desc:错误描述
    """

    def __init__(self, code: 'IoTxAlgorithmCode'):
        self.code = code.code
        self.desc = code.message
        self.data = []

    def set_code(self, code: 'IoTxAlgorithmCode'):
        self.code = code.code
        self.desc = code.message

    def append(self, algo_event: 'IoTxAlgorithmEvent'):
        self.data.append(algo_event)

    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__)


class IoTxAlgorithmEvent(object):
    """
    报警事件基类
    Attributes:
        alarmType: 报警类型
    """

    def __init__(self, alarmtype: 'IoTxAlgorithmEventType'):
        self.alarmType = alarmtype.value

    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__)


class IoTxClothesCountEvent(IoTxAlgorithmEvent):
    """
      特征提取
      Attributes:
          feature:特征值
      """

    def __init__(self):
        IoTxAlgorithmEvent.__init__(self, IoTxAlgorithmEventType.ClothesCount)
        self.left = 0.0
        self.top = 0.0
        self.width = 0.0
        self.height = 0.0
        self.display_name = ''


class IoTxObjectDetectionEvent(IoTxAlgorithmEvent):
    """
      特征提取
      Attributes:
          feature:特征值
      """

    def __init__(self):
        IoTxAlgorithmEvent.__init__(self, IoTxAlgorithmEventType.ObjectDetection)
        self.left = 0.0
        self.top = 0.0
        self.width = 0.0
        self.height = 0.0
        self.display_name = ''


class IoTxIllegalParkingEvent(IoTxAlgorithmEvent):
    """
    违章停车事件
    Attributes:
        rect:[0.1,0.2,0.3,0.4] 归一化
        plateNumber:车牌号
        brandName:车辆型号
        colorName:车辆颜色
        typeName:车辆类型
    """

    def __init__(self):
        IoTxAlgorithmEvent.__init__(self, IoTxAlgorithmEventType.IllegalParking)
        self.rect = []
        self.plateNumber = "A12345"
        self.brandCode = "04D5CE3F8452449bBE5E6972271A58C6"
        self.brandName = "大众-桑塔纳2000-19951998"
        self.colorCode = 0
        self.colorName = "白色"
        self.typeCode = 1
        self.typeName = "轿车"


class IoTxIllegalSaleEvent(IoTxAlgorithmEvent):
    """
    占道经营事件
    Attributes:
        rect:[0.1,0.2,0.3,0.4] 归一化
    """

    def __init__(self):
        IoTxAlgorithmEvent.__init__(self, IoTxAlgorithmEventType.IllegalSale)
        self.rect = []


class IoTxFaceDetectEvent(IoTxAlgorithmEvent):
    """
    人脸检测事件
    Attributes:
        rect:[0.1,0.2,0.3,0.4] 归一化
        probability:相似度
    """

    def __init__(self):
        IoTxAlgorithmEvent.__init__(self, IoTxAlgorithmEventType.FaceDetect)
        self.rect = []
        self.probability = 0.5
        self.head_pose_ypr = []


class IoTxFaceQCheckEvent(IoTxAlgorithmEvent):
    """
    人脸质量检测
    Attributes:
        score:质量分，满分为1
    """

    def __init__(self):
        IoTxAlgorithmEvent.__init__(self, IoTxAlgorithmEventType.FaceQCheck)
        self.score = 0.5


class IoTxFaceRecognizeEvent(IoTxAlgorithmEvent):
    """
      特征提取
      Attributes:
          feature:特征值
      """

    def __init__(self):
        IoTxAlgorithmEvent.__init__(self, IoTxAlgorithmEventType.FaceRecognize)
        self.feature = []


class IoTxHumanDetectRecognizeEvent(IoTxAlgorithmEvent):
    """
      特征提取
      Attributes:
          attr:描述
      """

    def __init__(self):
        IoTxAlgorithmEvent.__init__(self, IoTxAlgorithmEventType.HumanDetect)
        self.attr = ""


class IoTxBikesRecognitionEvent(IoTxAlgorithmEvent):
    """
    车辆识别事件
    Attributes:
        rect:[0.1,0.2,0.3,0.4] 归一化
        Sex:性别
        Age:年龄
        UpperType:上身穿着类型
        BottomType:下身穿着类型
        typeName:摩托车类型
    """

    def __init__(self):
        IoTxAlgorithmEvent.__init__(self, IoTxAlgorithmEventType.BikesRecognition)
        self.rect = []
        self.Sex = "男"
        self.Age = "青年"
        self.UpperType = "长袖"
        self.BottomType = "长裤"
        self.typeName = "摩托车"


class IoTxPedestrainsRecognitionEvent(IoTxAlgorithmEvent):
    """
    车辆识别事件
    Attributes:
        rect:[0.1,0.2,0.3,0.4] 归一化
        Sex:性别
        Age:年龄
        UpperType:上身穿着类型
        BottomType:下身穿着类型
        typeName:行人类型
    """

    def __init__(self):
        IoTxAlgorithmEvent.__init__(self, IoTxAlgorithmEventType.PedestrainsRecognition)
        self.rect = []
        self.Sex = "男"
        self.Age = "青年"
        self.UpperType = "长袖"
        self.BottomType = "长裤"
        self.typeName = "行人"


class IoTxVehiclesRecognitionEvent(IoTxAlgorithmEvent):
    """
    车辆识别事件
    Attributes:
        rect:[0.1,0.2,0.3,0.4] 归一化
        plateNumber:车牌号
        brandName:车辆型号
        colorName:车辆颜色
        typeName:车辆类型
    """

    def __init__(self):
        IoTxAlgorithmEvent.__init__(self, IoTxAlgorithmEventType.VehiclesRecognitionEvent)
        self.rect = []
        self.plateNumber = "A12345"
        self.brandCode = "04D5CE3F8452449bBE5E6972271A58C6"
        self.brandName = "大众-桑塔纳2000-19951998"
        self.colorCode = 0
        self.colorName = "白色"
        self.typeCode = 1
        self.typeName = "轿车"


class IoTxAgeGenderRecognitionEvent(IoTxAlgorithmEvent):
    """
      年龄性别识别事件
      Attributes:
          age: 年龄
          gender: female的概率
    """

    def __init__(self):
        IoTxAlgorithmEvent.__init__(self, IoTxAlgorithmEventType.AgeGenderRecognition)
        self.age = 18.0
        self.gender = 0.0


class IoTxEmotionsRecognitionEvent(IoTxAlgorithmEvent):
    """
      表情识别事件
      Attributes:
          neutral_prob: 'neutral'的置信度
          happy_prob: 'happy'的置信度
          sad_prob: 'sad'的置信度
          surprise_prob: 'surprise'的置信度
          anger_prob: 'anger'的置信度
    """

    def __init__(self):
        IoTxAlgorithmEvent.__init__(self, IoTxAlgorithmEventType.EmotionsRecognition)
        self.neutral_prob = 0.0
        self.happy_prob = 0.0
        self.sad_prob = 0.0
        self.surprise_prob = 0.0
        self.anger_prob = 0.0


class HumanPosesEstimationEvent(IoTxAlgorithmEvent):
    """
      表情识别事件
      Attributes:
          neutral_prob: 'neutral'的置信度

    """

    def __init__(self):
        IoTxAlgorithmEvent.__init__(self, IoTxAlgorithmEventType.HumanPosesEstimation)
        self.neutral_prob = 0.0


class VehicleLicensePlateDetectionEvent(IoTxAlgorithmEvent):
    """
      车辆和车牌检测事件
      Attributes:
          detection_type: 检测类型："vehicle", "license_plate"
          rect: [0.1,0.2,0.3,0.4] 归一化
    """

    def __init__(self):
        IoTxAlgorithmEvent.__init__(self, IoTxAlgorithmEventType.VehicleLicensePlateDetection)
        self.detection_type = "vehicle"
        self.rect = []


class LicensePlateRecognitionEvent(IoTxAlgorithmEvent):
    """
      车牌识别事件
      Attributes:
          plate_number: 车牌号码
    """

    def __init__(self):
        IoTxAlgorithmEvent.__init__(self, IoTxAlgorithmEventType.LicensePlateRecognition)
        self.plate_number = ""

