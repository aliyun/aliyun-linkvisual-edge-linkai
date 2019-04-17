# -*- coding: UTF-8 -*-

from linkai.algo_result import IoTxAlgorithmEvent
import json
import uuid

PIC_PATH = "static/images/"


class AlgorithmData(object):
    """
    算法数据
    """

    def __init__(self, algorithm, event: 'IoTxAlgorithmEvent'):
        if event is not None:
            self.alarmType = event.alarmType
        else:
            self.alarmType = -1
        self.algorithm = algorithm
        self.data = event


class AlgorithmEvent(object):
    """
    算法事件
    """

    def __init__(self, device_id, capture_time, pic_filename, algorithm, event: 'IoTxAlgorithmEvent', oss_file_url,
                 typ="IntelligentAlarmEvent"):
        self.deviceId = device_id
        self.time = capture_time
        self.value = AlgorithmData(algorithm, event)
        self.type = typ
        if pic_filename is not None:
            self.url = oss_file_url
            self.ossPic = pic_filename
            self.algo_id = algorithm
        else:
            self.id = uuid.uuid4().hex
            self.ossPic = ""
            self.url = ""

    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__)
