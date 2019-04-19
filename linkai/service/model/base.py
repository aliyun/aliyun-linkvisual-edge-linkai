#!/usr/bin/env python
# -*- coding: utf-8 -*-
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

from .iotx_codes import IoTxCode, IoTxCodes
import json


class BaseRequest(object):
    """ 基础请求
    """

    def dict2obj(self, dct, obj_tag):
        """
        字典表转换对象
        """
        for key, value in dct.items():
            if isinstance(value, dict):
                sub_obj = getattr(obj_tag, key)
                sub_dct = dct[key]
                if sub_dct is not None:
                    self.dict2obj(sub_dct, sub_obj)
                else:
                    setattr(obj_tag, key, None)
            elif isinstance(value, list):
                list_obj = list()
                for idx, item in enumerate(value):
                    if item is not None:
                        list_obj.append(item)
                setattr(obj_tag, key, list_obj)
            else:
                setattr(obj_tag, key, value)
        return obj_tag

    def init_from_json(self, json_str):
        try:
            ret = json.loads(json_str)
            self.dict2obj(ret, self)
        except Exception as e:
            print(e)
        return self


class BaseResponse(object):
    """ 基础回复
    """

    def __init__(self, iotx_code: 'IoTxCode' = IoTxCodes.SUCCESS):
        self.message = iotx_code.message
        self.result = iotx_code.code

    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__)
