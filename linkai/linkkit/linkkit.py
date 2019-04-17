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

import os
import logging
import threading
import queue
import urllib.request
import urllib.parse
import json
import hashlib
import hmac
import random
import ssl
import socket
import string
import time
import re
import paho.mqtt.client as mqtt
from enum import Enum
from paho.mqtt.client import MQTTMessage


class LinkKit(object):
    TAG_KEY = "attrKey"
    TAG_VALUE = "attrValue"

    class LinkKitState(Enum):
        INITIALIZED = 1
        CONNECTING = 2
        CONNECTED = 3
        DISCONNECTING = 4
        DISCONNECTED = 5
        DESTRUCTING = 6
        DESTRUCTED = 7

    class StateError(Exception):
        def __init__(self, err):
            Exception.__init__(self, err)

    class Shadow(object):
        def __init__(self):
            self.__version = None
            self.__timestamp = None
            self.__state = None
            self.__metadata = None
            self.__latest_shadow_lock = threading.Lock()
            self.__latest_received_time = None
            self.__lastest_received_payload = None

        def get_version(self):
            with self.__latest_shadow_lock:
                return self.__version

        def get_metadata(self):
            with self.__latest_shadow_lock:
                return self.__metadata

        def get_state(self):
            with self.__latest_shadow_lock:
                return self.__state

        def set_state(self, state):
            with self.__latest_shadow_lock:
                self.__state = state

        def set_metadata(self, metadata):
            with self.__latest_shadow_lock:
                self.__metadata = metadata

        def set_version(self, version):
            with self.__latest_shadow_lock:
                self.__version = version

        def set_timestamp(self, timestamp):
            with self.__latest_shadow_lock:
                self.__timestamp = timestamp

        def set_latest_recevied_time(self, timestamp):
            with self.__latest_shadow_lock:
                self.__latest_received_time = timestamp

        def get_latest_recevied_time(self):
            with self.__latest_shadow_lock:
                return self.__latest_received_time

        def set_latest_recevied_payload(self, payload):
            with self.__latest_shadow_lock:
                self.__latest_received_payload = payload

        def get_latest_recevied_payload(self):
            with self.__latest_shadow_lock:
                return self.__latest_received_payload

        def to_dict(self):
            return {'state': self.__state, 'metadata': self.__metadata, 'version': self.__version,
                    'timestamp': self.__timestamp}

        def to_json_string(self):
            return json.dumps(self.to_dict())

    class __HandlerTask(object):

        def __init__(self, logger=None):
            self.__logger = logger
            if self.__logger is not None:
                self.__logger.info("HandlerTask init enter")
            self.__message_queue = queue.Queue(20)
            self.__cmd_callback = {}
            self.__started = False
            self.__exited = False
            self.__thread = None
            pass

        def register_cmd_callback(self, cmd, callback):
            if self.__started is False:
                if cmd != "req_exit":
                    self.__cmd_callback[cmd] = callback
                    return 0
                else:
                    return 1
                pass
            else:
                return 2
            pass

        def post_message(self, cmd, value):
            self.__logger.debug("post_message :%r " % cmd)
            if self.__started and self.__exited is False:
                try:
                    self.__message_queue.put((cmd, value), timeout=5)
                except queue.Full as e:
                    self.__logger.error("queue full: %r" % e)
                    return False
                self.__logger.debug("post_message success")
                return True
            self.__logger.debug("post_message fail started:%r,exited:%r" % (self.__started, self.__exited))
            return False
            pass

        def start(self):
            if self.__logger is not None:
                self.__logger.info("HandlerTask start")
            if self.__started is False:
                if self.__logger is not None:
                    self.__logger.info("HandlerTask try start")
                self.__exited = False
                self.__started = True
                self.__message_queue = queue.Queue(20)
                self.__thread = threading.Thread(target=self.__thread_runnable)
                self.__thread.daemon = True
                self.__thread.start()
                return 0
            return 1

        def stop(self):
            if self.__started and self.__exited is False:
                self.__exited = True
                self.__message_queue.put(("req_exit", None))

        def wait_stop(self):
            if self.__started is True:
                self.__thread.join()

        def __thread_runnable(self):
            if self.__logger is not None:
                self.__logger.debug("thread runnable enter")
            while True:
                cmd, value = self.__message_queue.get()
                self.__logger.debug("thread runnable pop cmd:%r" % cmd)
                if cmd == "req_exit":
                    break
                if self.__cmd_callback[cmd] is not None:
                    try:
                        self.__cmd_callback[cmd](value)
                    except Exception as e:
                        if self.__logger is not None:
                            self.__logger.error("thread runnable raise exception:%s" % e)
            self.__started = False
            if self.__logger is not None:
                self.__logger.debug("thread runnable exit")
            pass

    class LoopThread(object):
        def __init__(self, logger=None):
            self.__logger = logger
            if logger is not None:
                self.__logger.info("LoopThread init enter")
            self.__callback = None
            self.__thread = None
            self.__started = False
            self.__req_wait = threading.Event()
            if logger is not None:
                self.__logger.info("LoopThread init exit")

        def start(self, callback):
            if self.__started is True:
                self.__logger.info("LoopThread already ")
                return 1
            else:
                self.__callback = callback
                self.__thread = threading.Thread(target=self.__thread_main)
                self.__thread.daemon = True
                self.__thread.start()
                return 0

        def stop(self):
            self.__req_wait.wait()
            self.__req_wait.clear()

        def __thread_main(self):
            self.__started = True
            try:
                if self.__logger is not None:
                    self.__logger.debug("LoopThread thread enter")
                if self.__callback is not None:
                    self.__callback()
                if self.__logger is not None:
                    self.__logger.debug("LoopThread thread exit")
            except Exception as e:
                self.__logger.error("LoopThread thread Exception:" + str(e))
            self.__started = False
            self.__req_wait.set()

    class __LinkKitLog(object):
        def __init__(self):
            self.__logger = logging.getLogger("linkkit")
            self.__enabled = False
            pass

        def enable_logger(self):
            self.__enabled = True

        def disable_logger(self):
            self.__enabled = False

        def is_enabled(self):
            return self.__enabled

        def config_logger(self, level):
            self.__logger.setLevel(level)

        def debug(self, fmt, *args):
            if self.__enabled:
                self.__logger.debug(fmt, *args)

        def warring(self, fmt, *args):
            if self.__enabled:
                self.__logger.warning(fmt, *args)

        def info(self, fmt, *args):
            if self.__enabled:
                self.__logger.info(fmt, *args)

        def error(self, fmt, *args):
            if self.__enabled:
                self.__logger.error(fmt, *args)

        def critical(self, fmt, *args):
            if self.__enabled:
                self.__logger.critical(fmt, *args)

    __USER_TOPIC_PREFIX = "/%s/%s/%s"
    __ALIYUN_BROKER_CA_DATA = "\
-----BEGIN CERTIFICATE-----\n\
MIIDdTCCAl2gAwIBAgILBAAAAAABFUtaw5QwDQYJKoZIhvcNAQEFBQAwVzELMAkG\
A1UEBhMCQkUxGTAXBgNVBAoTEEdsb2JhbFNpZ24gbnYtc2ExEDAOBgNVBAsTB1Jv\
b3QgQ0ExGzAZBgNVBAMTEkdsb2JhbFNpZ24gUm9vdCBDQTAeFw05ODA5MDExMjAw\
MDBaFw0yODAxMjgxMjAwMDBaMFcxCzAJBgNVBAYTAkJFMRkwFwYDVQQKExBHbG9i\
YWxTaWduIG52LXNhMRAwDgYDVQQLEwdSb290IENBMRswGQYDVQQDExJHbG9iYWxT\
aWduIFJvb3QgQ0EwggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEKAoIBAQDaDuaZ\
jc6j40+Kfvvxi4Mla+pIH/EqsLmVEQS98GPR4mdmzxzdzxtIK+6NiY6arymAZavp\
xy0Sy6scTHAHoT0KMM0VjU/43dSMUBUc71DuxC73/OlS8pF94G3VNTCOXkNz8kHp\
1Wrjsok6Vjk4bwY8iGlbKk3Fp1S4bInMm/k8yuX9ifUSPJJ4ltbcdG6TRGHRjcdG\
snUOhugZitVtbNV4FpWi6cgKOOvyJBNPc1STE4U6G7weNLWLBYy5d4ux2x8gkasJ\
U26Qzns3dLlwR5EiUWMWea6xrkEmCMgZK9FGqkjWZCrXgzT/LCrBbBlDSgeF59N8\
9iFo7+ryUp9/k5DPAgMBAAGjQjBAMA4GA1UdDwEB/wQEAwIBBjAPBgNVHRMBAf8E\
BTADAQH/MB0GA1UdDgQWBBRge2YaRQ2XyolQL30EzTSo//z9SzANBgkqhkiG9w0B\
AQUFAAOCAQEA1nPnfE920I2/7LqivjTFKDK1fPxsnCwrvQmeU79rXqoRSLblCKOz\
yj1hTdNGCbM+w6DjY1Ub8rrvrTnhQ7k4o+YviiY776BQVvnGCv04zcQLcFGUl5gE\
38NflNUVyRRBnMRddWQVDf9VMOyGj/8N7yy5Y0b2qvzfvGn9LhJIZJrglfCm7ymP\
AbEVtQwdpf5pLGkkeB6zpxxxYu7KyJesF12KwvhHhm4qxFYxldBniYUr+WymXUad\
DKqC5JlR3XC321Y9YeRq4VzW9v493kHMB65jUr9TU/Qr6cf9tveCX4XSQRjbgbME\
HMUfpIBvFSDJ3gyICh3WZlXi/EjJKSZp4A==\n\
-----END CERTIFICATE-----"

    def __init__(self, host_name, product_key, device_name, device_secret,
                 product_secret=None, user_data=None):
        # logging configs
        self.__just_for_pycharm_autocomplete = False

        def __str_is_empty(value):
            if value is None or value == "":
                return True
            else:
                return False

        # param check
        if __str_is_empty(host_name):
            raise ValueError("host_name wrong")
        if __str_is_empty(product_key):
            raise ValueError("product key wrong")
        if __str_is_empty(device_name):
            raise ValueError("device name wrong")
        if __str_is_empty(device_secret) and __str_is_empty(product_secret):
            raise ValueError("device secret & product secret are both empty")

        self.__link_log = LinkKit.__LinkKitLog()
        self.__PahoLog = logging.getLogger("Paho")
        self.__PahoLog.setLevel(logging.DEBUG)

        # config internal property
        self.__host_name = host_name
        self.__product_key = product_key
        self.__device_name = device_name
        self.__device_secret = device_secret
        self.__product_secret = product_secret
        self.__user_data = user_data
        self.__device_interface_info = ""
        self.__device_mac = None
        self.__cellular_IMEI = None
        self.__cellular_ICCID = None
        self.__cellular_IMSI = None
        self.__cellular_MSISDN = None
        self.__mqtt_client = None
        self.__sdk_version = "1.0.0"
        self.__sdk_program_language = "Python"

        self.__mqtt_port = 1883
        self.__mqtt_protocol = "MQTTv311"
        self.__mqtt_transport = "TCP"
        self.__mqtt_secure = "TLS"
        self.__mqtt_keep_alive = 60
        self.__mqtt_clean_session = True
        self.__mqtt_max_inflight_message = 20
        self.__mqtt_max_queued_message = 40
        self.__mqtt_auto_reconnect_min_sec = 1
        self.__mqtt_auto_reconnect_max_sec = 60
        self.__mqtt_auto_reconnect_sec = 0
        self.__mqtt_request_timeout = 10
        self.__linkkit_state = LinkKit.LinkKitState.INITIALIZED
        self.__aliyun_broker_ca_data = self.__ALIYUN_BROKER_CA_DATA

        self.__latest_shadow = LinkKit.Shadow()

        # aliyun IoT callbacks
        self.__on_device_dynamic_register = None

        # mqtt callbacks
        self.__on_connect = None
        self.__on_disconnect = None
        self.__on_publish_topic = None
        self.__on_subscribe_topic = None
        self.__on_unsubscribe_topic = None
        self.__on_topic_message = None

        self.__on_topic_rrpc_message = None
        self.__on_subscribe_rrpc_topic = None
        self.__on_unsubscribe_rrpc_topic = None

        # thing model callbacks
        self.__on_thing_create = None
        self.__on_thing_enable = None
        self.__on_thing_disable = None
        self.__on_thing_raw_data_arrived = None
        self.__on_thing_raw_data_post = None
        self.__on_thing_call_service = None
        self.__on_thing_prop_changed = None
        self.__on_thing_event_post = None
        self.__on_thing_prop_post = None
        self.__on_thing_shadow_get = None
        self.__on_thing_device_info_update = None
        self.__on_thing_device_info_delete = None

        self.__user_topics = {}
        self.__user_topics_subscribe_request = {}
        self.__user_topics_unsubscribe_request = {}
        self.__user_topics_request_lock = threading.Lock()
        self.__user_topics_unsubscribe_request_lock = threading.Lock()

        self.__user_rrpc_topics = {}
        self.__user_rrpc_topics_lock = threading.RLock()
        self.__user_rrpc_topics_subscribe_request = {}
        self.__user_rrpc_topics_unsubscribe_request = {}
        self.__user_rrpc_topics_subscribe_request_lock = threading.RLock()
        self.__user_rrpc_topics_unsubscribe_request_lock = threading.RLock()
        self.__user_rrpc_request_ids = []
        self.__user_rrpc_request_id_index_map = {}
        self.__user_rrpc_request_ids_lock = threading.RLock()
        self.__user_rrpc_request_max_len = 100

        # things topic - Alink
        self.__thing_topic_prop_post = '/sys/%s/%s/thing/event/property/post' % \
                                       (self.__product_key, self.__device_name)
        self.__thing_topic_prop_post_reply = self.__thing_topic_prop_post + "_reply"
        self.__thing_topic_prop_set = '/sys/%s/%s/thing/service/property/set' % \
                                      (self.__product_key, self.__device_name)
        self.__thing_topic_prop_set_reply = self.__thing_topic_prop_set + "_reply"
        self.__thing_topic_prop_get = '/sys/%s/%s/thing/service/property/get' % \
                                      (self.__product_key, self.__device_name)
        self.__thing_topic_event_post_pattern = '/sys/%s/%s/thing/event/%s/post'
        self.__thing_prop_post_mid = {}
        self.__thing_prop_post_mid_lock = threading.Lock()
        self.__thing_prop_set_reply_mid = {}
        self.__thing_prop_set_reply_mid_lock = threading.Lock()
        # event:post topic
        self.__thing_topic_event_post = {}
        self.__thing_topic_event_post_reply = set()
        self.__thing_events = set()
        self.__thing_request_id_max = 1000000
        self.__thing_request_value = 0
        self.__thing_request_id = {}
        self.__thing_request_id_lock = threading.Lock()
        self.__thing_event_post_mid = {}
        self.__thing_event_post_mid_lock = threading.Lock()

        self.__thing_topic_shadow_get = '/shadow/get/%s/%s' % \
                                        (self.__product_key, self.__device_name)
        self.__thing_topic_shadow_update = '/shadow/update/%s/%s' % \
                                           (self.__product_key, self.__device_name)
        self.__thing_shadow_mid = {}
        self.__thing_shadow_mid_lock = threading.Lock()

        # service topic
        self.__thing_topic_service_pattern = '/sys/%s/%s/thing/service/%s'
        self.__thing_topic_services = set()
        self.__thing_topic_services_reply = set()
        self.__thing_services = set()
        self.__thing_answer_service_mid = {}
        self.__thing_answer_service_mid_lock = threading.Lock()

        # thing topic - raw
        self.__thing_topic_raw_up = '/sys/%s/%s/thing/model/up_raw' % (self.__product_key, self.__device_name)
        self.__thing_topic_raw_up_reply = self.__thing_topic_raw_up + "_reply"
        self.__thing_topic_raw_down = '/sys/%s/%s/thing/model/down_raw' % (self.__product_key, self.__device_name)
        self.__thing_topic_raw_down_reply = self.__thing_topic_raw_down + "_reply"
        self.__thing_raw_up_mid = {}
        self.__thing_raw_up_mid_lock = threading.Lock()
        self.__thing_raw_down_reply_mid = {}
        self.__thing_raw_down_reply_mid_lock = threading.Lock()

        # thing topic - device_info
        self.__thing_topic_update_device_info_up = '/sys/%s/%s/thing/deviceinfo/update' % (
        self.__product_key, self.__device_name)
        self.__thing_topic_update_device_info_reply = self.__thing_topic_update_device_info_up + "_reply"
        self.__thing_topic_delete_device_info_up = '/sys/%s/%s/thing/deviceinfo/delete' % (
        self.__product_key, self.__device_name)
        self.__thing_topic_delete_device_info_reply = self.__thing_topic_delete_device_info_up + "_reply"
        self.__thing_update_device_info_up_mid = {}
        self.__thing_update_device_info_up_mid_lock = threading.Lock()
        self.__thing_delete_device_info_up_mid = {}
        self.__thing_delete_device_info_up_mid_lock = threading.Lock()

        # properties
        self.__thing_properties_set = set()
        self.__thing_properties_get = set()
        self.__thing_properties_post = set()

        # thing enable mid
        self.__thing_subscribe_sys_request = False
        self.__thing_subscribe_sys_request_mid = {}
        self.__thing_subscribe_sys_request_lock = threading.Lock()

        # thing setup state
        self.__thing_setup_state = False
        self.__thing_raw_only = False
        self.__thing_enable_state = False

        if self.__just_for_pycharm_autocomplete:
            self.__mqtt_client = mqtt.Client()

        # device interface info
        self.__device_info_topic = "/sys/%s/%s/thing/deviceinfo/update" % (self.__product_key, self.__device_name)
        self.__device_info_topic_reply = self.__device_info_topic + "_reply"
        self.__device_info_mid_lock = threading.Lock()
        self.__device_info_mid = {}

        # connect_async
        self.__connect_async_req = False
        self.__worker_loop_exit_req = False
        self.__worker_loop_runing_state = False
        self.__worker_loop_exit_req_lock = threading.Lock()

        # loop thread
        self.__loop_thread = LinkKit.LoopThread(self.__link_log)

        # HandlerTask
        self.__handler_task = LinkKit.__HandlerTask(self.__link_log)
        self.__handler_task_cmd_on_connect = "on_connect"
        self.__handler_task_cmd_on_disconnect = "on_disconnect"
        self.__handler_task_cmd_on_message = "on_message"
        self.__handler_task_cmd_on_publish = "on_publish"
        self.__handler_task_cmd_on_subscribe = "on_subscribe"
        self.__handler_task_cmd_on_unsubscribe = "on_unsubscribe"
        self.__handler_task.register_cmd_callback(self.__handler_task_cmd_on_connect,
                                                  self.__handler_task_on_connect_callback)
        self.__handler_task.register_cmd_callback(self.__handler_task_cmd_on_disconnect,
                                                  self.__handler_task_on_disconnect_callback)
        self.__handler_task.register_cmd_callback(self.__handler_task_cmd_on_message,
                                                  self.__handler_task_on_message_callback)
        self.__handler_task.register_cmd_callback(self.__handler_task_cmd_on_publish,
                                                  self.__handler_task_on_publish_callback)
        self.__handler_task.register_cmd_callback(self.__handler_task_cmd_on_subscribe,
                                                  self.__handler_task_on_subscribe_callback)
        self.__handler_task.register_cmd_callback(self.__handler_task_cmd_on_unsubscribe,
                                                  self.__handler_task_on_unsubscribe_callback)
        self.__handler_task.start()

        pass

    @property
    def on_device_dynamic_register(self):
        return None

    @on_device_dynamic_register.setter
    def on_device_dynamic_register(self, value):
        self.__on_device_dynamic_register = value

    @property
    def on_connect(self):
        return self.__on_connect

    @on_connect.setter
    def on_connect(self, value):
        self.__on_connect = value
        pass

    @property
    def on_disconnect(self):
        return self.__on_disconnect

    @on_disconnect.setter
    def on_disconnect(self, value):
        self.__on_disconnect = value

    @property
    def on_publish_topic(self):
        return None

    @on_publish_topic.setter
    def on_publish_topic(self, value):
        self.__on_publish_topic = value

    @property
    def on_subscribe_topic(self):
        return None

    @on_subscribe_topic.setter
    def on_subscribe_topic(self, value):
        self.__on_subscribe_topic = value

    @property
    def on_unsubscribe_topic(self):
        return None

    @on_unsubscribe_topic.setter
    def on_unsubscribe_topic(self, value):
        self.__on_unsubscribe_topic = value

    @property
    def on_topic_message(self):
        return None

    @on_topic_message.setter
    def on_topic_message(self, value):
        self.__on_topic_message = value

    @property
    def on_topic_rrpc_message(self):
        return None

    @on_topic_rrpc_message.setter
    def on_topic_rrpc_message(self, value):
        self.__on_topic_rrpc_message = value

    @property
    def on_thing_create(self):
        return None

    @on_thing_create.setter
    def on_thing_create(self, value):
        self.__on_thing_create = value

    @property
    def on_thing_enable(self):
        return None

    @on_thing_enable.setter
    def on_thing_enable(self, value):
        self.__on_thing_enable = value

    @property
    def on_thing_disable(self):
        return None

    @on_thing_disable.setter
    def on_thing_disable(self, value):
        self.__on_thing_disable = value

    @property
    def on_thing_raw_data_arrived(self):
        return None

    @on_thing_raw_data_arrived.setter
    def on_thing_raw_data_arrived(self, value):
        self.__on_thing_raw_data_arrived = value

    @property
    def on_thing_raw_data_post(self):
        return self.__on_thing_raw_data_post

    @property
    def on_thing_device_info_update(self):
        return self.__on_thing_device_info_update

    @on_thing_device_info_update.setter
    def on_thing_device_info_update(self, value):
        self.__on_thing_device_info_update = value

    @property
    def on_thing_device_info_delete(self):
        return self.__on_thing_device_info_delete

    @on_thing_device_info_delete.setter
    def on_thing_device_info_delete(self, value):
        self.__on_thing_device_info_delete = value

    @on_thing_raw_data_post.setter
    def on_thing_raw_data_post(self, value):
        self.__on_thing_raw_data_post = value

    @property
    def on_thing_call_service(self):
        return None

    @on_thing_call_service.setter
    def on_thing_call_service(self, value):
        self.__on_thing_call_service = value

    @property
    def on_thing_prop_changed(self):
        return None

    @on_thing_prop_changed.setter
    def on_thing_prop_changed(self, value):
        self.__on_thing_prop_changed = value

    @property
    def on_thing_event_post(self):
        return self.__on_thing_event_post

    @on_thing_event_post.setter
    def on_thing_event_post(self, value):
        self.__on_thing_event_post = value

    @property
    def on_thing_prop_post(self):
        return self.__on_thing_prop_post

    @on_thing_prop_post.setter
    def on_thing_prop_post(self, value):
        self.__on_thing_prop_post = value

    @property
    def on_thing_shadow_get(self):
        return self.__on_thing_shadow_get

    @on_thing_shadow_get.setter
    def on_thing_shadow_get(self, value):
        self.__on_thing_shadow_get = value

    def enable_logger(self, level):
        self.__link_log.config_logger(level)
        self.__link_log.enable_logger()
        if self.__mqtt_client is not None:
            self.__mqtt_client.enable_logger(self.__PahoLog)
        self.__PahoLog.setLevel(level)

    def disable_logger(self):
        self.__link_log.disable_logger()
        if self.__mqtt_client is not None:
            self.__mqtt_client.disable_logger()

    def config_logger(self, level):
        self.__link_log.config_logger(level)
        if self.__mqtt_client is not None:
            self.__PahoLog.setLevel(level)

    def config_mqtt(self, port=1883, protocol="MQTTv311", transport="TCP",
                    secure="TLS", keep_alive=60, clean_session=True,
                    max_inflight_message=20, max_queued_message=40,
                    auto_reconnect_min_sec=1,
                    auto_reconnect_max_sec=60,
                    cadata=None):
        if self.__linkkit_state is not LinkKit.LinkKitState.INITIALIZED:
            raise LinkKit.StateError("not in INITIALIZED state")
        if port < 1 or port > 65535:
            raise ValueError("port wrong")
        if protocol != "MQTTv311" and protocol != "MQTTv31":
            raise ValueError("protocol wrong")
        if transport != "TCP":
            raise ValueError("transport wrong")
        if secure != "TLS" and secure != "":
            raise ValueError("secure wrong")
        if keep_alive < 60 or keep_alive > 180:
            raise ValueError("keep_alive range wrong")
        if clean_session is not True and clean_session is not False:
            raise ValueError("clean session wrong")
        if max_queued_message < 0:
            raise ValueError("max_queued_message wrong")
        if max_inflight_message < 0:
            raise ValueError("max_inflight_message wrong")
        if auto_reconnect_min_sec < 1 or auto_reconnect_min_sec > 120 * 60:
            raise ValueError("auto_reconnect_min_sec wrong")
        if auto_reconnect_max_sec < 1 or auto_reconnect_max_sec > 120 * 60:
            raise ValueError("auto_reconnect_max_sec wrong")
        if auto_reconnect_min_sec > auto_reconnect_max_sec:
            raise ValueError("auto_reconnect_max_sec less than auto_reconnect_min_sec")

        self.__link_log.info("config_mqtt enter")
        if self.__linkkit_state == LinkKit.LinkKitState.INITIALIZED:
            if port is not None:
                self.__mqtt_port = port
            if protocol is not None:
                self.__mqtt_protocol = protocol
            if transport is not None:
                self.__mqtt_transport = transport
            if secure is not None:
                self.__mqtt_secure = secure
            if keep_alive is not None:
                self.__mqtt_keep_alive = keep_alive
            if clean_session is not None:
                self.__mqtt_clean_session = clean_session
            if max_inflight_message is not None:
                self.__mqtt_max_inflight_message = max_inflight_message
            if max_queued_message is not None:
                self.__mqtt_max_queued_message = max_queued_message
            if auto_reconnect_min_sec is not None:
                self.__mqtt_auto_reconnect_min_sec = auto_reconnect_min_sec
            if auto_reconnect_max_sec is not None:
                self.__mqtt_auto_reconnect_max_sec = auto_reconnect_max_sec
            if cadata is not None:
                self.__aliyun_broker_ca_data = cadata

    def config_device_info(self, interface_info):
        if self.__linkkit_state is not LinkKit.LinkKitState.INITIALIZED:
            raise LinkKit.StateError("LinkKit object not in INITIALIZED")
        if not isinstance(interface_info, str):
            raise ValueError("interface info must be string")
        if len(interface_info) > 160:
            return 1
        self.__device_interface_info = interface_info
        return 0

    def get_product(self):
        return self.__product_key

    def get_device_name(self):
        return self.__device_name

    def __upload_device_interface_info(self):
        request_id = self.__get_thing_request_id()
        payload = {
            "id": request_id,
            "version": "1.0",
            "params": [
                {
                    "domain": "SYSTEM",
                    "attrKey": "SYS_SDK_LANGUAGE",
                    "attrValue": self.__sdk_program_language
                },
                {
                    "domain": "SYSTEM",
                    "attrKey": "SYS_LP_SDK_VERSION",
                    "attrValue": self.__sdk_version
                },
                {
                    "domain": "SYSTEM",
                    "attrKey": "SYS_SDK_IF_INFO",
                    "attrValue": self.__device_interface_info
                },
            ],
            "method": "thing.deviceinfo.update"
        }
        with self.__device_info_mid_lock:
            rc, mid = self.__mqtt_client.publish(self.__device_info_topic, json.dumps(payload), 0)
            if rc == mqtt.MQTT_ERR_SUCCESS:
                self.__device_info_mid[mid] = self.__timestamp()
                return 0
            else:
                return 1

    def destruct(self):
        if self.__linkkit_state is LinkKit.LinkKitState.DESTRUCTED:
            raise LinkKit.StateError("LinkKit object has already destructed")
        self.__link_log.debug("destruct enter")
        if self.__linkkit_state == LinkKit.LinkKitState.CONNECTED or \
                        self.__linkkit_state == LinkKit.LinkKitState.CONNECTING:
            self.__linkkit_state = LinkKit.LinkKitState.DESTRUCTING
            if self.__connect_async_req:
                with self.__worker_loop_exit_req_lock:
                    self.__worker_loop_exit_req = True
            if self.__mqtt_client is not None:
                self.__mqtt_client.disconnect()
            self.__handler_task.wait_stop()
        else:
            self.__linkkit_state = LinkKit.LinkKitState.DESTRUCTING
            if self.__connect_async_req:
                with self.__worker_loop_exit_req_lock:
                    self.__worker_loop_exit_req = True
            self.__handler_task.stop()
            self.__handler_task.wait_stop()
            self.__linkkit_state = LinkKit.LinkKitState.DESTRUCTED
        pass

    def check_state(self):
        return self.__linkkit_state

    @staticmethod
    def __generate_random_str(randomlength=16):
        """
        generate radom string
        """
        random_str = ""
        for i in range(randomlength):
            random_str += random.choice(string.digits + string.ascii_letters)
        return random_str

    def __dynamic_register_device(self):
        pk = self.__product_key
        ps = self.__product_secret
        dn = self.__device_name
        random_str = self.__generate_random_str(15)
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH, cadata=self.__aliyun_broker_ca_data)
        sign_content = "deviceName%sproductKey%srandom%s" % (dn, pk, random_str)
        sign = hmac.new(ps.encode("utf-8"), sign_content.encode("utf-8"), hashlib.sha256).hexdigest()
        post_data = {
            "productKey": pk,
            "deviceName": dn,
            "random": random_str,
            "sign": sign,
            "signMethod": "hmacsha256"
        }
        data = urllib.parse.urlencode(post_data)
        data = data.encode('ascii')
        request_url = "https://iot-auth.%s.aliyuncs.com/auth/register/device" % self.__host_name
        with urllib.request.urlopen(request_url, data, context=context) as f:
            reply_data = f.read().decode('utf-8')
            reply_obj = json.loads(reply_data)
            if reply_obj["code"] == 200:
                reply_obj_data = reply_obj["data"]
                if reply_obj_data is not None:
                    return 0, reply_obj_data["deviceSecret"]
                    pass
            else:
                return 1, reply_obj["message"]

    def __config_mqtt_client_internal(self):
        self.__link_log.info("start connect")

        timestamp = str(int(time.time()))
        if self.__mqtt_secure == "TLS":
            client_id = "%s&%s|securemode=2,signmethod=hmacsha1,ext=1,timestamp=%s|" \
                        % (self.__product_key, self.__device_name, timestamp)
        else:
            client_id = "%s&%s|securemode=3,signmethod=hmacsha1,ext=1,timestamp=%s|" \
                        % (self.__product_key, self.__device_name, timestamp)
        username = self.__device_name + "&" + self.__product_key

        # calc sign
        sign_content = "clientId%sdeviceName%sproductKey%stimestamp%s" % (
            self.__product_key + "&" + self.__device_name,
            self.__device_name,
            self.__product_key,
            timestamp)
        #            timestamp)
        password = hmac.new(self.__device_secret.encode("utf-8"), sign_content.encode("utf-8"),
                            hashlib.sha1).hexdigest()

        # mqtt client start initialize
        mqtt_protocol_version = mqtt.MQTTv311
        if self.__mqtt_protocol == "MQTTv311":
            mqtt_protocol_version = mqtt.MQTTv311
        elif self.__mqtt_protocol == "MQTTv31":
            mqtt_protocol_version = mqtt.MQTTv31
        self.__mqtt_client = mqtt.Client(client_id=client_id,
                                         clean_session=self.__mqtt_clean_session,
                                         protocol=mqtt_protocol_version)
        if self.__link_log.is_enabled():
            self.__mqtt_client.enable_logger(self.__PahoLog)
        self.__mqtt_client.username_pw_set(username, password)
        self.__mqtt_client.on_connect = self.__on_internal_connect
        self.__mqtt_client.on_disconnect = self.__on_internal_disconnect
        self.__mqtt_client.on_message = self.__on_internal_message
        self.__mqtt_client.on_publish = self.__on_internal_publish
        self.__mqtt_client.on_subscribe = self.__on_internal_subscribe
        self.__mqtt_client.on_unsubscribe = self.__on_internal_unsubscribe

        self.__mqtt_client.reconnect_delay_set(self.__mqtt_auto_reconnect_min_sec, self.__mqtt_auto_reconnect_max_sec)
        self.__mqtt_client.max_queued_messages_set(self.__mqtt_max_queued_message)
        self.__mqtt_client.max_inflight_messages_set(self.__mqtt_max_inflight_message)

        # mqtt set tls
        self.__link_log.debug("current working directory:" + os.getcwd())
        if self.__mqtt_secure == "TLS":
            context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH, cadata=self.__aliyun_broker_ca_data)
            self.__mqtt_client.tls_set_context(context)
        # mqtt client start connect
        if self.__host_name == "127.0.0.1" or self.__host_name == "localhost":
            self.__host_name_internal = self.__host_name
        elif self.__host_name == "10.125.3.189" or self.__host_name == "daily":
            self.__host_name_internal = "10.125.3.189"
        else:
            self.__host_name_internal = "%s.iot-as-mqtt.%s.aliyuncs.com" % \
                                        (self.__product_key, self.__host_name)
        pass

    def connect(self):
        if self.__linkkit_state is not LinkKit.LinkKitState.INITIALIZED:
            raise LinkKit.StateError("not in INITIALIZED state")
        if self.__device_secret is None or self.__device_secret == "":
            if self.__product_secret is None or self.__product_secret == "":
                raise ValueError("device Secret & product secret both empty")
            rc, value = self.__dynamic_register_device()
            if self.__on_device_dynamic_register is None:
                raise Exception("user not give on_device_dynamic_register")
            try:
                self.__on_device_dynamic_register(rc, value, self.__user_data)
                if rc == 0:
                    self.__device_secret = value
                else:
                    self.__link_log.error("dynamic register device fail:" + value)
                    return 1
            except Exception as e:
                self.__link_log.error(e)
                return 2
        self.__config_mqtt_client_internal()
        self.__mqtt_client.connect(host=self.__host_name_internal, port=self.__mqtt_port,
                                   keepalive=self.__mqtt_keep_alive)
        return 0

    def __connect_async_internal(self):
        if self.__device_secret is None or self.__device_secret == "":
            if self.__product_secret is None or self.__product_secret == "":
                raise ValueError("device Secret & product secret both empty")
            rc, value = self.__dynamic_register_device()
            if self.__on_device_dynamic_register is None:
                raise Exception("user not give on_device_dynamic_register")
            try:
                self.__on_device_dynamic_register(rc, value, self.__user_data)
                if rc == 0:
                    self.__device_secret = value
                else:
                    self.__link_log.error("dynamic register device fail:" + value)
                    return 1
            except Exception as e:
                self.__link_log.error(e)
                return 2
        self.__config_mqtt_client_internal()
        self.__mqtt_client.connect_async(host=self.__host_name_internal, port=self.__mqtt_port,
                                         keepalive=self.__mqtt_keep_alive)
        self.__mqtt_client.loop_start()

    def connect_async(self):
        self.__link_log.debug("connect_async")
        if self.__linkkit_state not in (LinkKit.LinkKitState.INITIALIZED, LinkKit.LinkKitState.DISCONNECTED):
            raise LinkKit.StateError("not in INITIALIZED or DISCONNECTED state")
        self.__connect_async_req = True
        with self.__worker_loop_exit_req_lock:
            self.__worker_loop_exit_req = False
        return self.__loop_thread.start(self.__loop_forever_internal)

    def disconnect(self):
        self.__link_log.debug("disconnect")
        if self.__linkkit_state is not LinkKit.LinkKitState.CONNECTED:
            raise LinkKit.StateError("not in CONNECTED state")
        self.__linkkit_state = LinkKit.LinkKitState.DISCONNECTING
        if self.__connect_async_req:
            with self.__worker_loop_exit_req_lock:
                self.__worker_loop_exit_req = True
        self.__mqtt_client.disconnect()
        self.__loop_thread.stop()

    @staticmethod
    def __check_topic_string(topic):
        if len(topic) > 128 or len(topic) == 0:
            raise ValueError("topic string length too long,need decrease %d bytes" % (128 - len(topic)))

    def publish_topic(self, topic, payload=None, qos=1):
        if self.__linkkit_state is not LinkKit.LinkKitState.CONNECTED:
            raise LinkKit.StateError("not in CONNECTED state")
        if topic is None or len(topic) == 0:
            raise ValueError('Invalid topic.')
        if qos != 0 and qos != 1:
            raise ValueError('Invalid qos.')
        self.__check_topic_string(topic)
        rc, mid = self.__mqtt_client.publish(topic, payload, qos)
        if rc == 0:
            return 0, mid
        else:
            return 1, None

    def subscribe_topic(self, topic, qos=1):
        if self.__linkkit_state is not LinkKit.LinkKitState.CONNECTED:
            raise LinkKit.StateError("not in CONNECTED state")
        if isinstance(topic, tuple):
            topic, qos = topic

        if isinstance(topic, str):
            if qos < 0 or qos > 1:
                raise ValueError('Invalid QoS level.')
            if topic is None or len(topic) == 0:
                raise ValueError('Invalid topic.')
            self.__check_topic_string(topic)
            if topic not in self.__user_topics:
                self.__user_topics_request_lock.acquire()
                ret = self.__mqtt_client.subscribe(topic, qos)
                rc, mid = ret
                if rc == mqtt.MQTT_ERR_SUCCESS:
                    self.__user_topics_subscribe_request[mid] = [(topic, qos)]
                self.__user_topics_request_lock.release()
                if rc == mqtt.MQTT_ERR_SUCCESS:
                    return 0, mid
                if rc == mqtt.MQTT_ERR_NO_CONN:
                    return 2, None
                return 3, None
            else:
                return 1, None
        elif isinstance(topic, list):
            topic_qos_list = []
            user_topic_dict = {}
            for t, q in topic:
                if q < 0 or q > 1:
                    raise ValueError('Invalid QoS level.')
                if t is None or len(t) == 0 or not isinstance(t, str):
                    raise ValueError('Invalid topic.')
                self.__check_topic_string(t)
                user_topic_dict[t] = q
                topic_qos_list.append((t, q))
            self.__user_topics_request_lock.acquire()
            ret = self.__mqtt_client.subscribe(topic_qos_list)
            rc, mid = ret
            if rc == mqtt.MQTT_ERR_SUCCESS:
                self.__user_topics_subscribe_request[mid] = topic_qos_list
                self.__link_log.debug("__user_topics_subscribe_request add mid:%d" % mid)
            self.__user_topics_request_lock.release()
            return rc, mid
        else:
            raise ValueError('Parameter type wrong')

    def unsubscribe_topic(self, topic):
        if self.__linkkit_state is not LinkKit.LinkKitState.CONNECTED:
            raise LinkKit.StateError("not in CONNECTED state")
        unsubscribe_topics = []
        if topic is None or topic == "":
            raise ValueError('Invalid topic.')
        if isinstance(topic, str):
            self.__check_topic_string(topic)
            if topic not in self.__user_topics:
                return 1, None
            unsubscribe_topics.append(topic)
        elif isinstance(topic, list):
            for one_topic in topic:
                self.__check_topic_string(one_topic)
                if one_topic in self.__user_topics:
                    unsubscribe_topics.append(one_topic)
                else:
                    pass
        with self.__user_topics_unsubscribe_request_lock:
            if len(unsubscribe_topics) == 0:
                return 2, None
            ret = self.__mqtt_client.unsubscribe(unsubscribe_topics)
            rc, mid = ret
            if rc == mqtt.MQTT_ERR_SUCCESS:
                self.__user_topics_unsubscribe_request[mid] = unsubscribe_topics
                return ret
            else:
                return 1, None

    def __make_rrpc_topic(self, topic):
        return '/ext/rrpc/+%s' % (topic)

    def subscribe_rrpc_topic(self, topic):
        if self.__linkkit_state is not LinkKit.LinkKitState.CONNECTED:
            raise LinkKit.StateError("not in CONNECTED state")
        qos = 0
        if isinstance(topic, str):
            if topic is None or len(topic) == 0:
                raise ValueError('Invalid topic.')
            self.__check_topic_string(topic)
            topic = self.__tidy_topic(topic)
            rrpc_topic = self.__make_rrpc_topic(topic)
            with self.__user_rrpc_topics_lock:
                not_exist = topic not in self.__user_rrpc_topics.keys()
            if not_exist:
                with self.__user_rrpc_topics_lock:
                    self.__user_rrpc_topics[topic] = qos
                with self.__user_rrpc_topics_subscribe_request_lock:
                    ret = self.__mqtt_client.subscribe(rrpc_topic, qos)
                    rc, mid = ret
                    if rc == mqtt.MQTT_ERR_SUCCESS:
                        self.__user_rrpc_topics_subscribe_request[mid] = [(rrpc_topic, qos)]
                    if rc == mqtt.MQTT_ERR_SUCCESS:
                        return 0, mid
                    if rc == mqtt.MQTT_ERR_NO_CONN:
                        return 2, None
                    return 3, None
            else:
                return 1, None
        elif isinstance(topic, list):
            topic_qos_list = []
            for t in topic:
                if t is None or len(t) == 0 or not isinstance(t, str):
                    raise ValueError('Invalid topic.')
                self.__check_topic_string(t)
                t = self.__tidy_topic(t)
                rrpc_t = self.__make_rrpc_topic(t)
                with self.__user_rrpc_topics_lock:
                    self.__user_rrpc_topics[t] = qos
                topic_qos_list.append((rrpc_t, qos))
            with self.__user_rrpc_topics_subscribe_request_lock:
                ret = self.__mqtt_client.subscribe(topic_qos_list)
                rc, mid = ret
                if rc == mqtt.MQTT_ERR_SUCCESS:
                    self.__user_rrpc_topics_subscribe_request[mid] = topic_qos_list
                    self.__link_log.debug("__user_rrpc_topics_subscribe_request add mid:%d" % mid)
                return rc, mid
        else:
            raise ValueError('Parameter type wrong')

    def unsubscribe_rrpc_topic(self, topic):
        if self.__linkkit_state is not LinkKit.LinkKitState.CONNECTED:
            raise LinkKit.StateError("not in CONNECTED state")
        unsubscribe_topics = []
        if topic is None or topic == "":
            raise ValueError('Invalid topic.')
        if isinstance(topic, str):
            self.__check_topic_string(topic)
            topic = self.__tidy_topic(topic)
            with self.__user_rrpc_topics_lock:
                if topic not in self.__user_rrpc_topics:
                    return 1, None
            rrpc_topic = self.__make_rrpc_topic(topic)
            unsubscribe_topics.append(rrpc_topic)
            with self.__user_rrpc_topics_lock:
                del self.__user_rrpc_topics[topic]

        elif isinstance(topic, list):
            for one_topic in topic:
                self.__check_topic_string(one_topic)
                one_topic = self.__tidy_topic(one_topic)
                with self.__user_rrpc_topics_lock:
                    if one_topic in self.__user_rrpc_topics:
                        rrpc_topic = self.__make_rrpc_topic(one_topic)
                        unsubscribe_topics.append(rrpc_topic)
                        del self.__user_rrpc_topics[one_topic]
                    else:
                        pass
        with self.__user_rrpc_topics_unsubscribe_request_lock:
            if len(unsubscribe_topics) == 0:
                return 2, None
            ret = self.__mqtt_client.unsubscribe(unsubscribe_topics)
            rc, mid = ret
            if rc == mqtt.MQTT_ERR_SUCCESS:
                self.__user_rrpc_topics_unsubscribe_request[mid] = unsubscribe_topics
                return ret
            else:
                return 1, None

    def __on_internal_connect_safe(self, client, user_data, session_flag, rc):
        if rc == 0:
            self.__reset_reconnect_wait()
        session_flag_internal = {'session present': session_flag}
        self.__handler_task.post_message(self.__handler_task_cmd_on_connect,
                                         (client, user_data, session_flag_internal, rc))

    def __loop_forever_internal(self):
        self.__link_log.debug("enter")
        self.__linkkit_state = LinkKit.LinkKitState.CONNECTING
        if self.__device_secret is None or self.__device_secret == "":
            rc, value = self.__dynamic_register_device()
            try:
                self.__on_device_dynamic_register(rc, value, self.__user_data)
                if rc == 0:
                    self.__device_secret = value
                else:
                    self.__link_log.error("dynamic register device fail:" + value)
                    self.__linkkit_state = LinkKit.LinkKitState.INITIALIZED
                    return 1
            except Exception as e:
                self.__link_log.error(e)
                self.__linkkit_state = LinkKit.LinkKitState.INITIALIZED
                return 2
        try:
            self.__config_mqtt_client_internal()
        except ssl.SSLError as e:
            self.__link_log.error("config mqtt raise exception:" + str(e))
            self.__linkkit_state = LinkKit.LinkKitState.INITIALIZED
            self.__on_internal_connect_safe(None, None, 0, 6)
            return

        try:
            self.__mqtt_client.connect_async(host=self.__host_name_internal, port=self.__mqtt_port,
                                             keepalive=self.__mqtt_keep_alive)
        except Exception as e:
            self.__link_log.error("__loop_forever_internal connect raise exception:" + str(e))
            self.__linkkit_state = LinkKit.LinkKitState.INITIALIZED
            self.__on_internal_connect_safe(None, None, 0, 7)
            return
        while True:
            if self.__worker_loop_exit_req:
                if self.__linkkit_state == LinkKit.LinkKitState.DESTRUCTING:
                    self.__handler_task.stop()
                    self.__linkkit_state = LinkKit.LinkKitState.DESTRUCTED
                break
            try:
                self.__linkkit_state = LinkKit.LinkKitState.CONNECTING
                self.__mqtt_client.reconnect()
            except (socket.error, OSError) as e:
                self.__link_log.error(e)
                # if isinstance(e, socket.timeout):
                #     self.__link_log.error("connect timeout")
                #     self.__on_internal_connect_safe(None, None, 0, 8)
                #     self.__reconnect_wait()
                #     continue
                # if isinstance(e, ssl.SSLError):
                #     self.__on_internal_connect_safe(None, None, 0, 6)
                #     return
                if self.__linkkit_state == LinkKit.LinkKitState.CONNECTING:
                    self.__linkkit_state = LinkKit.LinkKitState.DISCONNECTED
                self.__on_internal_connect_safe(None, None, 0, 9)
                if self.__linkkit_state == LinkKit.LinkKitState.DESTRUCTING:
                    self.__handler_task.stop()
                    self.__linkkit_state = LinkKit.LinkKitState.DESTRUCTED
                    break
                self.__reconnect_wait()
                continue
                # 1. ca wrong 2.socket create timeout 3.connect timeout, call on_connect error
            # connect success
            rc = mqtt.MQTT_ERR_SUCCESS
            while rc == mqtt.MQTT_ERR_SUCCESS:
                rc = self.__mqtt_client.loop(self.__mqtt_request_timeout, 1)
                self.__clean_timeout_message()
                self.__clean_thing_timeout_request_id()
            if self.__linkkit_state == LinkKit.LinkKitState.CONNECTED:
                self.__on_internal_disconnect(None, None, 1)
            self.__link_log.info("loop return:%r" % rc)

            if self.__worker_loop_exit_req:
                if self.__linkkit_state == LinkKit.LinkKitState.DESTRUCTING:
                    self.__handler_task.stop()
                    self.__linkkit_state = LinkKit.LinkKitState.DESTRUCTED
                break
            self.__reconnect_wait()

    def __clean_timeout_message(self):
        # self.__link_log.debug("__clean_timeout_message enter")
        expire_timestamp = self.__timestamp() - self.__mqtt_request_timeout * 1000
        with self.__thing_prop_post_mid_lock:
            self.__clean_timeout_message_item(self.__thing_prop_post_mid, expire_timestamp)
        with self.__thing_event_post_mid_lock:
            self.__clean_timeout_message_item(self.__thing_event_post_mid, expire_timestamp)
        with self.__thing_answer_service_mid_lock:
            self.__clean_timeout_message_item(self.__thing_answer_service_mid, expire_timestamp)
        with self.__thing_raw_up_mid_lock:
            self.__clean_timeout_message_item(self.__thing_raw_up_mid, expire_timestamp)
        with self.__thing_raw_down_reply_mid_lock:
            self.__clean_timeout_message_item(self.__thing_raw_down_reply_mid, expire_timestamp)
        with self.__thing_prop_set_reply_mid_lock:
            self.__clean_timeout_message_item(self.__thing_prop_set_reply_mid, expire_timestamp)
        self.__clean_timeout_message_item(self.__thing_subscribe_sys_request_mid, expire_timestamp)
        self.__clean_timeout_message_item(self.__device_info_mid, expire_timestamp)
        # self.__link_log.debug("__clean_timeout_message exit")

    def __clean_timeout_message_item(self, mids, expire_time):
        for mid in list(mids.keys()):
            if mids[mid] < expire_time:
                timestamp = mids.pop(mid)
                self.__link_log.error("__clean_timeout_message_item pop:%r,timestamp:%r", mid, timestamp)

    def __reconnect_wait(self):
        if self.__mqtt_auto_reconnect_sec == 0:
            self.__mqtt_auto_reconnect_sec = self.__mqtt_auto_reconnect_min_sec
        else:
            self.__mqtt_auto_reconnect_sec = min(self.__mqtt_auto_reconnect_sec * 2, self.__mqtt_auto_reconnect_max_sec)
            self.__mqtt_auto_reconnect_sec += random.randint(1, self.__mqtt_auto_reconnect_sec)
        time.sleep(self.__mqtt_auto_reconnect_sec)
        pass

    def __reset_reconnect_wait(self):
        self.__mqtt_auto_reconnect_sec = 0

    def start_worker_loop(self):
        pass

    def thing_setup(self, file=None):
        if self.__linkkit_state is not LinkKit.LinkKitState.INITIALIZED:
            raise LinkKit.StateError("not in INITIALIZED state")
        if self.__thing_setup_state:
            return 1
        if file is None:
            self.__thing_raw_only = True
            self.__thing_setup_state = True
            return 0
        try:
            with open(file, encoding='utf-8') as f:
                tsl = json.load(f)
                index = 0
                while index < len(tsl["events"]):
                    identifier = tsl["events"][index]["identifier"]
                    if identifier == "post":
                        output_data = tsl["events"][index]["outputData"]
                        output_data_index = 0
                        while output_data_index < len(output_data):
                            output_data_item = output_data[output_data_index]["identifier"]
                            self.__thing_properties_post.add(output_data_item)
                            output_data_index += 1
                    else:
                        self.__thing_events.add(identifier)
                    index += 1
                index = 0
                while index < len(tsl["services"]):
                    identifier = tsl["services"][index]["identifier"]
                    if identifier == "set":
                        input_data = tsl["services"][index]["inputData"]
                        input_data_index = 0
                        while input_data_index < len(input_data):
                            input_data_item = input_data[input_data_index]
                            self.__thing_properties_set.add(input_data_item["identifier"])
                            input_data_index += 1
                    elif identifier == "get":
                        output_data = tsl["services"][index]["outputData"]
                        output_data_index = 0
                        while output_data_index < len(output_data):
                            output_data_item = output_data[output_data_index]
                            self.__thing_properties_get.add(output_data_item["identifier"])
                            output_data_index += 1
                    else:
                        self.__thing_services.add(identifier)
                        service_reply_topic = self.__thing_topic_service_pattern % (self.__product_key,
                                                                                    self.__device_name,
                                                                                    identifier + "_reply")
                        self.__thing_topic_services_reply.add(service_reply_topic)
                    index += 1

                for event in self.__thing_events:
                    post_topic = self.__thing_topic_event_post_pattern % \
                                 (self.__product_key, self.__device_name, event)
                    self.__thing_topic_event_post[event] = post_topic
                    self.__thing_topic_event_post_reply.add(post_topic + "_reply")
                # service topic
                for service in self.__thing_services:
                    self.__thing_topic_services.add(self.__thing_topic_service_pattern %
                                                    (self.__product_key, self.__device_name, service))

        except Exception as e:
            self.__link_log.info("file open error:" + str(e))
            return 2
        self.__thing_setup_state = True
        return 0

    def __subscribe_sys_topic(self):
        subscribe_sys_topics = [(self.__device_info_topic_reply, 0)]
        if self.__thing_setup_state:
            if self.__thing_raw_only:
                thing_subscribe_topics = [(self.__thing_topic_raw_down, 0),
                                          (self.__thing_topic_raw_up_reply, 0)]
            else:
                thing_subscribe_topics = [(self.__thing_topic_prop_set, 0),
                                          (self.__thing_topic_prop_get, 0),
                                          (self.__thing_topic_raw_down, 0),
                                          (self.__thing_topic_prop_post_reply, 0),
                                          (self.__thing_topic_raw_up_reply, 0),
                                          (self.__thing_topic_update_device_info_reply, 0),
                                          (self.__thing_topic_delete_device_info_reply, 0),
                                          (self.__thing_topic_shadow_get, 0)
                                          ]
                for topic in self.__thing_topic_services:
                    thing_subscribe_topics.append((topic, 0))
                for topic in self.__thing_topic_event_post_reply:
                    thing_subscribe_topics.append((topic, 0))
            subscribe_sys_topics += thing_subscribe_topics
        with self.__thing_subscribe_sys_request_lock:
            rc, mid = self.__mqtt_client.subscribe(subscribe_sys_topics)
            # self.__link_log("topic:%s" % str(thing_subscribe_topics))
            if rc == mqtt.MQTT_ERR_SUCCESS:
                self.__thing_subscribe_sys_request = True
                self.__thing_subscribe_sys_request_mid[mid] = self.__timestamp()
                return 0
            else:
                return 1

    def thing_raw_post_data(self, payload):
        if self.__linkkit_state is not LinkKit.LinkKitState.CONNECTED:
            raise LinkKit.StateError("not in CONNECTED state")
        with self.__thing_raw_up_mid_lock:
            rc, mid = self.__mqtt_client.publish(self.__thing_topic_raw_up, payload, 0)
            if rc == mqtt.MQTT_ERR_SUCCESS:
                self.__thing_raw_up_mid[mid] = self.__timestamp()
                return 0
        return 1

    def thing_raw_data_reply(self, payload):
        if self.__linkkit_state is not LinkKit.LinkKitState.CONNECTED:
            raise LinkKit.StateError("not in CONNECTED state")
        with self.__thing_raw_down_reply_mid_lock:
            rc, mid = self.__mqtt_client.publish(self.__thing_topic_raw_down_reply, payload, 0)
            if rc == mqtt.MQTT_ERR_SUCCESS:
                self.__thing_raw_down_reply_mid[mid] = self.__timestamp()
                return 0
        return 1

    def thing_update_device_info(self, payload):
        if self.__linkkit_state is not LinkKit.LinkKitState.CONNECTED:
            raise LinkKit.StateError("not in CONNECTED state")
        if not self.__thing_setup_state or not self.__thing_enable_state:
            return 1, None
        request_id = self.__get_thing_request_id()
        with self.__thing_update_device_info_up_mid_lock:
            rc, mid = self.__mqtt_client.publish(self.__thing_topic_update_device_info_up,
                                                 self.__pack_alink_request(request_id, "thing.deviceinfo.update",
                                                                           payload),
                                                 0)
            if rc == mqtt.MQTT_ERR_SUCCESS:
                self.__thing_update_device_info_up_mid[mid] = self.__timestamp()
                return rc, request_id
        return 1, None

    def thing_delete_device_info(self, payload):
        if self.__linkkit_state is not LinkKit.LinkKitState.CONNECTED:
            raise LinkKit.StateError("not in CONNECTED state")
        if not self.__thing_setup_state or not self.__thing_enable_state:
            return 1
        request_id = self.__get_thing_request_id()
        with self.__thing_delete_device_info_up_mid_lock:
            rc, mid = self.__mqtt_client.publish(self.__thing_topic_delete_device_info_up,
                                                 self.__pack_alink_request(request_id, "thing.deviceinfo.delete",
                                                                           payload),
                                                 0)
            if rc == mqtt.MQTT_ERR_SUCCESS:
                self.__thing_delete_device_info_up_mid[mid] = self.__timestamp()
                return rc, request_id
        return 1, None

    def thing_update_tags(self, tagMap):
        if not isinstance(tagMap, dict):
            raise ValueError("tagMap must be a dictionary")
            return 1, None

        payload = []
        for (k, v) in tagMap.items():
            payload.append({LinkKit.TAG_KEY: k, LinkKit.TAG_VALUE: v})
        return self.thing_update_device_info(payload)

    def thing_remove_tags(self, tagKeys):
        if not isinstance(tagKeys, list) and not isinstance(tagKeys, tuple):
            raise ValueError("tagKeys must be a list or tuple")
            return 1, None

        payload = []
        for tagKey in tagKeys:
            payload.append({LinkKit.TAG_KEY: tagKey})
        return self.thing_delete_device_info(payload)

    def __pack_alink_request(self, request_id, method, params):
        request = {
            "id": request_id,
            "version": "1.0",
            "params": params,
            "method": method
        }
        return json.dumps(request)

    def thing_answer_service(self, identifier, request_id, code, data=None):
        if self.__linkkit_state is not LinkKit.LinkKitState.CONNECTED:
            raise LinkKit.StateError("not in CONNECTED state")
        if not self.__thing_setup_state or not self.__thing_enable_state:
            return 1
        if data is None:
            data = {}
        response = {
            "id": request_id,
            "code": code,
            "data": data
        }

        item = self.__pop_rrpc_service('alink_' + request_id)
        if item:
            service_reply_topic = item['topic']
        else:
            service_reply_topic = self.__thing_topic_service_pattern % (self.__product_key,
                                                                        self.__device_name,
                                                                        identifier + "_reply")
        with self.__thing_answer_service_mid_lock:
            rc, mid = self.__mqtt_client.publish(service_reply_topic, json.dumps(response), 0)
            if rc == mqtt.MQTT_ERR_SUCCESS:
                self.__thing_answer_service_mid[mid] = self.__timestamp()
                return 0
        return 1

    def __get_thing_request_id(self):
        with self.__thing_request_id_lock:
            self.__thing_request_value += 1
            if self.__thing_request_value > self.__thing_request_id_max:
                self.__thing_request_value = 0
            if len(self.__thing_request_id) > self.__mqtt_max_queued_message:
                return None
            if self.__thing_request_value not in self.__thing_request_id:
                self.__thing_request_id[self.__thing_request_value] = self.__timestamp()
                self.__link_log.debug("__get_thing_request_id pop:%r" % self.__thing_request_value)
                return str(self.__thing_request_value)
            return None

    def __back_thing_request_id(self, post_id):
        with self.__thing_request_id_lock:
            try:
                self.__thing_request_id.pop(int(post_id))
            except Exception as e:
                self.__link_log.error("__back_thing_request_id pop:%r,%r" % (post_id, e))

    def __reset_thing_request_id(self):
        with self.__thing_request_id_lock:
            self.__thing_request_value = 0
            self.__thing_request_id.clear()

    def __clean_thing_timeout_request_id(self):
        with self.__thing_request_id_lock:
            expire_timestamp = self.__timestamp() - self.__mqtt_request_timeout * 1000
            for request_id in list(self.__thing_request_id.keys()):
                if self.__thing_request_id[request_id] < expire_timestamp:
                    timestamp = self.__thing_request_id.pop(request_id)
                    self.__link_log.error("__clean_thing_timeout_request_id pop:%r,timestamp:%r", request_id, timestamp)

    def thing_trigger_event(self, event_tuple):
        if self.__linkkit_state is not LinkKit.LinkKitState.CONNECTED:
            raise LinkKit.StateError("not in CONNECTED state")
        if not self.__thing_setup_state or not self.__thing_enable_state:
            return 1
        if isinstance(event_tuple, tuple):
            event, params = event_tuple
        else:
            return 1, None
        if event not in self.__thing_topic_event_post.keys():
            return 1, None
        request_id = self.__get_thing_request_id()
        if request_id is None:
            return 1
        request = {
            "id": request_id,
            "version": "1.0",
            "params": {
                "value": params,
            },
            "method": "thing.event.%s.post" % event
        }
        with self.__thing_event_post_mid_lock:
            event_topic = self.__thing_topic_event_post[event]
            self.__link_log.debug("thing_trigger_event publish topic")
            rc, mid = self.__mqtt_client.publish(event_topic, json.dumps(request), 0)
            self.__link_log.debug("thing_trigger_event publish done")
            if rc == mqtt.MQTT_ERR_SUCCESS:
                self.__thing_event_post_mid[mid] = self.__timestamp()
                return 0, request_id
            else:
                return 1, None

    def thing_post_property(self, property_data):
        if self.__linkkit_state is not LinkKit.LinkKitState.CONNECTED:
            raise LinkKit.StateError("not in CONNECTED state")
        if not self.__thing_setup_state or not self.__thing_enable_state:
            return 1
        request_params = property_data
        request_id = self.__get_thing_request_id()
        if request_id is None:
            return 1
        request = {
            "id": request_id,
            "version": "1.0",
            "params": request_params,
            "method": "thing.event.property.post"
        }
        with self.__thing_prop_post_mid_lock:
            rc, mid = self.__mqtt_client.publish(self.__thing_topic_prop_post, json.dumps(request), 1)
            if rc == mqtt.MQTT_ERR_SUCCESS:
                self.__thing_prop_post_mid[mid] = self.__timestamp()
                return 0, request_id
            else:
                return 1, None
        pass

    def __on_internal_async_message(self, message):
        self.__link_log.debug("__on_internal_async_message topic:%r" % message.topic)
        if message.topic == self.__thing_topic_prop_set:
            payload = json.loads(message.payload)
            params = payload["params"]
            try:
                reply = {
                    "id": payload["id"],
                    "code": 200,
                    "data": {}
                }
                with self.__thing_prop_set_reply_mid_lock:
                    rc, mid = self.__mqtt_client.publish(self.__thing_topic_prop_set_reply, json.dumps(reply), 1)
                    if rc == 0:
                        self.__link_log.info("prop changed reply success,mid:%d" % mid)
                        self.__thing_prop_set_reply_mid[mid] = self.__timestamp()
                        self.__link_log.info("prop changed reply success")
                    else:
                        self.__link_log.info("prop changed reply fail")
                    pass
                self.__on_thing_prop_changed(params, self.__user_data)
            except Exception as e:
                self.__link_log.error("on_thing_prop_changed raise exception:%s" % e)
        elif message.topic == self.__device_info_topic_reply:
            payload = json.loads(message.payload)
            request_id = payload["id"]
            code = payload["code"]
            reply_message = payload["message"]
            data = payload["data"]
            self.__back_thing_request_id(request_id)
            if code != 200:
                self.__link_log.error("upload device info reply error:%s" % reply_message)
            try:
                if self.__on_thing_device_info_update != None:
                    self.__on_thing_device_info_update(request_id, code, data, reply_message, self.__user_data)
            except Exception as e:
                self.__link_log.error("__on_thing_device_info_update process raise exception:%s" % e)
            pass
        elif message.topic == self.__thing_topic_prop_post_reply:
            payload = json.loads(message.payload)
            request_id = payload["id"]
            code = payload["code"]
            data = payload["data"]
            reply_message = payload["message"]
            try:
                self.__on_thing_prop_post(request_id, code, data, reply_message, self.__user_data)
            except Exception as e:
                self.__link_log.error("on_thing_prop_post raise exception:%s" % e)
            self.__back_thing_request_id(request_id)
            pass
        elif message.topic == self.__thing_topic_prop_get:
            pass
        elif message.topic in self.__thing_topic_event_post_reply:
            event = message.topic.split('/', 7)[6]
            payload = json.loads(message.payload)
            request_id = payload["id"]
            code = payload["code"]
            data = payload["data"]
            reply_message = payload["message"]
            self.__link_log.info("on_thing_event_post message:%s" % reply_message)
            try:
                self.on_thing_event_post(event, request_id, code, data, reply_message, self.__user_data)
            except Exception as e:
                self.__link_log.error("on_thing_event_post raise exception:%s" % e)
            self.__back_thing_request_id(request_id)
            pass
        elif message.topic in self.__thing_topic_services:
            identifier = message.topic.split('/', 6)[6]
            payload = json.loads(message.payload)
            try:
                request_id = payload["id"]
                params = payload["params"]
                self.__on_thing_call_service(identifier, request_id, params, self.__user_data)
            except Exception as e:
                self.__link_log.error("on_thing_call_service raise exception: %s" % e)
        elif message.topic == self.__thing_topic_raw_down:
            try:
                self.__on_thing_raw_data_arrived(message.payload, self.__user_data)
            except Exception as e:
                self.__link_log.error("on_thing_raw_data_arrived process raise exception:%s" % e)
        elif message.topic == self.__thing_topic_raw_up_reply:
            try:
                self.__on_thing_raw_data_post(message.payload, self.__user_data)
            except Exception as e:
                self.__link_log.error("on_thing_raw_post_data process raise exception:%s" % e)
            pass
        elif message.topic == self.__thing_topic_update_device_info_reply:
            try:
                if self.__on_thing_device_info_update != None:
                    payload = json.loads(message.payload)
                    request_id = payload["id"]
                    code = payload["code"]
                    data = payload["data"]
                    msg = payload['message']
                    self.__on_thing_device_info_update(request_id, code, data, msg, self.__user_data)
            except Exception as e:
                self.__link_log.error("__on_thing_device_info_update process raise exception:%s" % e)
            pass
        elif message.topic == self.__thing_topic_delete_device_info_reply:
            try:
                if self.__on_thing_device_info_delete != None:
                    payload = json.loads(message.payload)
                    request_id = payload["id"]
                    code = payload["code"]
                    data = payload["data"]
                    msg = payload['message']
                    self.__on_thing_device_info_delete(request_id, code, data, msg, self.__user_data)
            except Exception as e:
                self.__link_log.error("__on_thing_device_info_update process raise exception:%s" % e)
            pass
        elif message.topic == self.__thing_topic_shadow_get:
            self.__try_parse_try_shadow(message.payload)
            try:
                if self.__on_thing_shadow_get != None:
                    self.__on_thing_shadow_get(json.loads(message.payload), self.__user_data)
            except Exception as e:
                self.__link_log.error("__on_thing_shadow_get process raise exception:%s" % e)
            pass
        elif message.topic.startswith("/ext/rrpc/"):
            self.__try_parse_rrpc_topic(message)
            pass
        elif message.topic in self.__user_topics and self.__on_topic_message is not None:
            try:
                self.__on_topic_message(message.topic, message.payload, message.qos, self.__user_data)
            except Exception as e:
                self.__link_log.error("on_topic_message process raise exception:%s" % e)
            pass
        else:
            self.__link_log.error("receive unscubscibe topic : %s" % message.topic)
        pass

    def __parse_raw_topic(self, topic):
        return re.search('/ext/rrpc/.*?(/.*)', topic).group(1)

    def __tidy_topic(self, topic):
        if topic == None:
            return None
        topic = topic.strip()
        if len(topic) == 0:
            return None
        if topic[0] != '/':
            topic = '/' + topic
        return topic

    def __push_rrpc_service(self, item):
        with self.__user_rrpc_request_ids_lock:
            if len(self.__user_rrpc_request_ids) > self.__user_rrpc_request_max_len:
                removed_item = self.__user_rrpc_request_ids.pop(0)
                del self.__user_rrpc_request_id_index_map[removed_item['id']]

        self.__user_rrpc_request_ids.append(item)
        self.__user_rrpc_request_id_index_map[item['id']] = 0

    def __pop_rrpc_service(self, id):
        with self.__user_rrpc_request_ids_lock:
            if id not in self.__user_rrpc_request_id_index_map:
                return None
            del self.__user_rrpc_request_id_index_map[id]
            for index in range(0, len(self.__user_rrpc_request_ids)):
                item = self.__user_rrpc_request_ids[index]
                if item['id'] == id:
                    del self.__user_rrpc_request_ids[index]
                    return item
            return None

    def thing_answer_rrpc(self, id, response):
        item = self.__pop_rrpc_service("rrpc_" + id)
        if item == None:
            self.__link_log.error("answer_rrpc_topic, the id does not exist: %s" % id)
            return 1, None
        rc, mid = self.__mqtt_client.publish(item['topic'], response, 0)
        self.__link_log.debug('reply topic:%s' % item['topic'])
        return rc, mid

    def __try_parse_rrpc_topic(self, message):
        self.__link_log.debug('receive a rrpc topic:%s' % message.topic)
        raw_topic = self.__parse_raw_topic(message.topic)
        # if it is a service, log it...
        if raw_topic.startswith('/sys') and raw_topic in self.__thing_topic_services:
            identifier = raw_topic.split('/', 6)[6]
            payload = json.loads(message.payload)
            try:
                request_id = payload["id"]
                params = payload["params"]
                item_id = 'alink_' + request_id
                item = {'id': item_id, 'request_id': request_id, 'payload': payload, 'identifier': identifier,
                        'topic': message.topic}
                self.__push_rrpc_service(item)
                self.__on_thing_call_service(identifier, request_id, params, self.__user_data)
            except Exception as e:
                self.__link_log.error("on_thing_call_service raise exception: %s" % e)
            return

        # parse
        with self.__user_rrpc_topics_subscribe_request_lock:
            with self.__user_rrpc_topics_lock:
                if raw_topic not in self.__user_rrpc_topics:
                    self.__link_log.error("%s is not in the rrpc-subscribed list" % raw_topic)
                    return
        if not self.__on_topic_rrpc_message:
            return
        try:
            rrpc_id = message.topic.split('/', 4)[3]
            item_id = 'rrpc_' + rrpc_id
            item = {'id': item_id, 'payload': message.payload, 'topic': message.topic}
            self.__push_rrpc_service(item)
            self.__on_topic_rrpc_message(rrpc_id, message.topic,
                                         message.payload,
                                         message.qos,
                                         self.__user_data)
            # self.__mqtt_client.publish(message.topic, response, 0)
            # self.__link_log.debug('reply topic:%s' % message.topic)
        except Exception as e:
            self.__link_log.error("on_topic_rrpc_message process raise exception:%r" % e)

    def __try_parse_try_shadow(self, payload):
        try:
            self.__latest_shadow.set_latest_recevied_time(self.__timestamp())
            self.__latest_shadow.set_latest_recevied_payload(payload)

            # parse the pay load
            msg = json.loads(payload)
            # set version
            if 'version' in msg:
                self.__latest_shadow.set_version(msg['version'])
            elif 'payload' in msg and 'version' in msg['payload']:
                self.__latest_shadow.set_version(msg['payload']['version'])

            # set timestamp
            if 'timestamp' in msg:
                self.__latest_shadow.set_timestamp(msg['timestamp'])
            elif 'payload' in msg and 'timestamp' in msg['payload']:
                self.__latest_shadow.set_timestamp(msg['payload']['timestamp'])

            # set state and metadata
            if 'payload' in msg and msg['payload']['status'] == 'success':
                if 'state' in msg['payload']:
                    self.__latest_shadow.set_state(msg['payload']['state'])
                if 'metadata' in msg['payload']:
                    self.__latest_shadow.set_metadata(msg['payload']['metadata'])
        except Exception as e:
            pass

    def thing_update_shadow(self, reported, version):
        request = {
            'state': {'reported': reported},
            'method': 'update',
            'version': version
        }
        return self.__thing_update_shadow(request)

    def thing_get_shadow(self):
        request = {'method': 'get'}
        return self.__thing_update_shadow(request)

    def local_get_latest_shadow(self):
        return self.__latest_shadow

    def __thing_update_shadow(self, request):
        if self.__linkkit_state is not LinkKit.LinkKitState.CONNECTED:
            raise LinkKit.StateError("not in CONNECTED state")
        if not self.__thing_setup_state or not self.__thing_enable_state:
            return 1, None
        with self.__thing_shadow_mid_lock:
            rc, mid = self.__mqtt_client.publish(self.__thing_topic_shadow_update,
                                                 json.dumps(request), 1)
            if rc == mqtt.MQTT_ERR_SUCCESS:
                self.__thing_shadow_mid[mid] = self.__timestamp()
                return 0, mid
            else:
                return 1, None

    def __on_internal_message(self, client, user_data, message):
        self.__link_log.info("__on_internal_message")
        self.__handler_task.post_message(self.__handler_task_cmd_on_message, (client, user_data, message))
        # self.__worker_thread.async_post_message(message)
        pass

    def __handler_task_on_message_callback(self, value):
        client, user_data, message = value
        self.__on_internal_async_message(message)

    def __on_internal_connect(self, client, user_data, session_flag, rc):
        self.__link_log.info("__on_internal_connect")
        if rc == 0:
            self.__reset_reconnect_wait()
            self.__subscribe_sys_topic()
            self.__upload_device_interface_info()
        self.__handler_task.post_message(self.__handler_task_cmd_on_connect, (client, user_data, session_flag, rc))

    def __handler_task_on_connect_callback(self, value):
        client, user_data, session_flag, rc = value
        self.__link_log.info("__on_internal_connect enter")
        self.__link_log.debug("session:%d, return code:%d" % (session_flag['session present'], rc))
        if rc == 0:
            self.__linkkit_state = LinkKit.LinkKitState.CONNECTED
            # self.__worker_thread.start()
        if self.__on_connect is not None:
            try:
                self.__on_connect(session_flag['session present'], rc, self.__user_data)
            except Exception as e:
                self.__link_log.error("on_connect process raise exception:%r" % e)
        pass

    def __on_internal_disconnect(self, client, user_data, rc):
        self.__link_log.info("__on_internal_disconnect enter")
        if self.__linkkit_state == LinkKit.LinkKitState.DESTRUCTING:
            self.__linkkit_state = LinkKit.LinkKitState.DESTRUCTED
        elif self.__linkkit_state == LinkKit.LinkKitState.DISCONNECTING:
            self.__linkkit_state = LinkKit.LinkKitState.DISCONNECTED
        elif self.__linkkit_state == LinkKit.LinkKitState.CONNECTED:
            self.__linkkit_state = LinkKit.LinkKitState.DISCONNECTED
        elif self.__linkkit_state == LinkKit.LinkKitState.DISCONNECTED:
            self.__link_log.error("__on_internal_disconnect enter from wrong state:%r" % self.__linkkit_state)
            return
        else:
            self.__link_log.error("__on_internal_disconnect enter from wrong state:%r" % self.__linkkit_state)
            return
        self.__user_topics.clear()
        self.__user_topics_subscribe_request.clear()
        self.__user_topics_unsubscribe_request.clear()

        self.__user_rrpc_topics.clear()
        self.__user_rrpc_topics_subscribe_request.clear()
        self.__user_rrpc_topics_unsubscribe_request.clear()

        self.__thing_prop_post_mid.clear()
        self.__thing_event_post_mid.clear()
        self.__thing_answer_service_mid.clear()
        self.__thing_raw_down_reply_mid.clear()
        self.__thing_raw_up_mid.clear()
        self.__thing_shadow_mid.clear()
        self.__device_info_mid.clear()
        self.__thing_update_device_info_up_mid.clear()
        self.__thing_delete_device_info_up_mid.clear()
        self.__handler_task.post_message(self.__handler_task_cmd_on_disconnect, (client, user_data, rc))
        if self.__linkkit_state == LinkKit.LinkKitState.DESTRUCTED:
            self.__handler_task.stop()

    def __handler_task_on_disconnect_callback(self, value):
        self.__link_log.info("__handler_task_on_disconnect_callback enter")
        client, user_data, rc = value
        if self.__thing_setup_state:
            if self.__thing_enable_state:
                self.__thing_enable_state = False
                if self.__on_thing_disable is not None:
                    try:
                        self.__on_thing_disable(self.__user_data)
                    except Exception as e:
                        self.__link_log.error("on_thing_disable process raise exception:%r" % e)
        if self.__on_disconnect is not None:
            try:
                self.__on_disconnect(rc, self.__user_data)
            except Exception as e:
                self.__link_log.error("on_disconnect process raise exception:%r" % e)

        pass

    def __on_internal_publish(self, client, user_data, mid):
        self.__handler_task.post_message(self.__handler_task_cmd_on_publish, (client, user_data, mid))

    def __handler_task_on_publish_callback(self, value):
        client, user_data, mid = value
        self.__link_log.debug("__on_internal_publish message:%d" % mid)
        with self.__thing_event_post_mid_lock:
            if mid in self.__thing_event_post_mid:
                self.__thing_event_post_mid.pop(mid)
                self.__link_log.debug("__on_internal_publish event post mid removed")
                return
        with self.__thing_prop_post_mid_lock:
            if mid in self.__thing_prop_post_mid:
                self.__thing_prop_post_mid.pop(mid)
                self.__link_log.debug("__on_internal_publish prop post mid removed")
                return
        with self.__thing_prop_set_reply_mid_lock:
            if mid in self.__thing_prop_set_reply_mid:
                self.__thing_prop_set_reply_mid.pop(mid)
                self.__link_log.debug("__on_internal_publish prop set reply mid removed")
                return
        with self.__thing_answer_service_mid_lock:
            if mid in self.__thing_answer_service_mid:
                self.__thing_answer_service_mid.pop(mid)
                self.__link_log.debug("__thing_answer_service_mid mid removed")
                return
        with self.__thing_raw_up_mid_lock:
            if mid in self.__thing_raw_up_mid:
                self.__thing_raw_up_mid.pop(mid)
                self.__link_log.debug("__thing_raw_up_mid mid removed")
                return
        with self.__thing_raw_down_reply_mid_lock:
            if mid in self.__thing_raw_down_reply_mid:
                self.__thing_raw_down_reply_mid.pop(mid)
                self.__link_log.debug("__thing_raw_down_reply_mid mid removed")
                return
        with self.__device_info_mid_lock:
            if mid in self.__device_info_mid:
                self.__device_info_mid.pop(mid)
                self.__link_log.debug("__device_info_mid mid removed")
                return
        with self.__thing_shadow_mid_lock:
            if mid in self.__thing_shadow_mid:
                self.__thing_shadow_mid.pop(mid)
                self.__link_log.debug("__thing_shadow_mid mid removed")
                return
        with self.__thing_update_device_info_up_mid_lock:
            if mid in self.__thing_update_device_info_up_mid:
                self.__thing_update_device_info_up_mid.pop(mid)
                self.__link_log.debug("__thing_update_device_info_up_mid mid removed")
                return
        with self.__thing_delete_device_info_up_mid_lock:
            if mid in self.__thing_delete_device_info_up_mid:
                self.__thing_delete_device_info_up_mid.pop(mid)
                self.__link_log.debug("__thing_delete_device_info_up_mid mid removed")
                return
        if self.__on_publish_topic is not None:
            self.__on_publish_topic(mid, self.__user_data)
        pass

    def __on_internal_subscribe(self, client, user_data, mid, granted_qos):
        self.__handler_task.post_message(self.__handler_task_cmd_on_subscribe, (client, user_data, mid, granted_qos))

    def __handler_task_on_subscribe_callback(self, value):
        client, user_data, mid, granted_qos = value
        self.__link_log.debug("__on_internal_subscribe mid:%d  granted_qos:%s" %
                              (mid, str(','.join('%s' % it for it in granted_qos))))
        if self.__thing_subscribe_sys_request and mid in self.__thing_subscribe_sys_request_mid:
            self.__thing_subscribe_sys_request_mid.pop(mid)
            self.__thing_subscribe_sys_request = False
            if self.__thing_setup_state:
                self.__thing_enable_state = True
                self.__on_thing_enable(self.__user_data)
            return
        # try to read rrpc
        with self.__user_rrpc_topics_subscribe_request_lock:
            if mid in self.__user_rrpc_topics_subscribe_request:
                self.__user_rrpc_topics_subscribe_request.pop(mid)
                if self.__on_subscribe_rrpc_topic:
                    try:
                        self.__on_subscribe_rrpc_topic(mid, granted_qos, self.__user_data)
                    except Exception as err:
                        self.__link_log.error('Caught exception in on_subscribe_topic: %s', err)
                return

        # try to read other topic
        topics_requests = None
        self.__user_topics_request_lock.acquire()
        if mid in self.__user_topics_subscribe_request:
            topics_requests = self.__user_topics_subscribe_request.pop(mid)
        self.__user_topics_request_lock.release()
        if topics_requests is not None:
            return_topics = []
            for index in range(len(topics_requests)):
                if granted_qos[index] < 0 or granted_qos[index] > 1:
                    self.__link_log.error("topics:%s, granted wrong:%d" %
                                          (topics_requests[index], granted_qos[index]))
                else:
                    self.__user_topics[topics_requests[index][0]] = granted_qos[index]
                return_topics.append((topics_requests[index], granted_qos[index]))
        if self.__on_subscribe_topic is not None:
            try:
                self.__on_subscribe_topic(mid, granted_qos, self.__user_data)
            except Exception as err:
                self.__link_log.error('Caught exception in on_subscribe_topic: %s', err)
        pass

    def __on_internal_unsubscribe(self, client, user_data, mid):
        self.__handler_task.post_message(self.__handler_task_cmd_on_unsubscribe, (client, user_data, mid))

    def __handler_task_on_unsubscribe_callback(self, value):
        client, user_data, mid = value
        self.__link_log.debug("__on_internal_unsubscribe mid:%d" % mid)
        unsubscribe_request = None
        # try to read rrpc
        with self.__user_rrpc_topics_unsubscribe_request_lock:
            if mid in self.__user_rrpc_topics_unsubscribe_request:
                self.__user_rrpc_topics_unsubscribe_request.pop(mid)
                if self.__on_unsubscribe_rrpc_topic:
                    try:
                        self.__on_unsubscribe_rrpc_topic(mid, self.__user_data)
                    except Exception as err:
                        self.__link_log.error('Caught exception in on_unsubscribe_rrpc_topic: %s', err)
                return

        with self.__user_topics_unsubscribe_request_lock:
            if mid in self.__user_topics_unsubscribe_request:
                unsubscribe_request = self.__user_topics_unsubscribe_request.pop(mid)
                pass
        if unsubscribe_request is not None:
            for t in unsubscribe_request:
                self.__link_log.debug("__user_topics:%s" % str(self.__user_topics))
                try:
                    self.__user_topics.pop(t)
                except Exception as e:
                    self.__link_log.error("__on_internal_unsubscribe e:" + str(e))
                    return
        if self.__on_unsubscribe_topic is not None:
            try:
                self.__on_unsubscribe_topic(mid, self.__user_data)
            except Exception as err:
                self.__link_log.error('Caught exception in on_unsubscribe_topic: %s', err)

    def dump_user_topics(self):
        return self.__user_topics

    @staticmethod
    def to_user_topic(topic):
        topic_section = topic.split('/', 3)
        user_topic = topic_section[3]
        return user_topic

    def to_full_topic(self, topic):
        return self.__USER_TOPIC_PREFIX % (self.__product_key, self.__device_name, topic)

    @staticmethod
    def __timestamp():
        return int(time.time() * 1000)
