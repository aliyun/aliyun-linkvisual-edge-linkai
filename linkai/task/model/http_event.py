from linkai.algo_result import IoTxAlgorithmEvent
import json


# HttpEventData 类， 包含在HttpEvent的data（类型是数组）list中
class HttpEventData(object):
    def __init__(self, crop_pic_name, event: 'IoTxAlgorithmEvent'):
        self.event = event  # 存放算法的单个目标检测结果， 同一张图片如果多张人脸则会有多个HttpEventData分开存
        self.pic_name = crop_pic_name


# HttpEvent
class HttpEvent(object):
    def __init__(self, device_id, capture_time, origin_pic_name):
        self.deviceId = device_id
        self.capture_time = capture_time
        self.origin_pic_name = origin_pic_name
        self.data = []  # list的元素为HttpEventData对象， 通过HttpEvent.data[index].event.rect 取算法的矩形框

    def append(self, event_data: 'HttpEventData'):
        self.data.append(event_data)

    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__)
