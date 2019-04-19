# -*- coding: UTF-8 -*-
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
