# -*- coding: UTF-8 -*-
import logging
import os

from linkai import conf
import oss2

log = logging.getLogger(__name__)


class OssClient(object):
    """ oss客户端

        oss客户端，提供上传本地文件，文件流，以及生成访问云端的url
    Attributes:
        bucket: oss bucket
    """

    def __init__(self):
        if "ACCESS_KEY_ID" in os.environ:
            self.access_key_id = os.environ["ACCESS_KEY_ID"]
        else:
            self.access_key_id = conf.get_string("OSS_CFG", "access_key_id")
        if "ACCESS_KEY_SECRET" in os.environ:
            self.access_key_secret = os.environ["ACCESS_KEY_SECRET"]
        else:
            self.access_key_secret = conf.get_string("OSS_CFG", "access_key_secret")
        if "BUCKET_NAME" in os.environ:
            self.bucket_name = os.environ["BUCKET_NAME"]
        else:
            self.bucket_name = conf.get_string("OSS_CFG", "bucket_name")
        if "ENDPOINT" in os.environ:
            self.endpoint = os.environ["ENDPOINT"]
        else:
            self.endpoint = conf.get_string("OSS_CFG", "endpoint")
        self.bucket = oss2.Bucket(oss2.Auth(self.access_key_id, self.access_key_secret), self.endpoint,
                                  self.bucket_name)
        return

    def __del__(self):
        pass

    def put_object_from_buffer(self, oss_filename, img_buffer, headers={'Content-Type': 'image/jpeg'}):
        try:
            self.bucket.put_object(key=oss_filename, data=img_buffer,
                                   headers=headers)
            log.debug("oss put_object_from_buffer file={} ok".format(oss_filename))
        except Exception as e:
            log.error("oss put_object_from_buffer file={} failed, error={}".format(oss_filename, e))

    def put_object_from_file(self, oss_filename, local_filename):
        try:
            self.bucket.put_object_from_file(oss_filename, local_filename)
            log.debug("oss put_object_from_file file={} ok".format(oss_filename))
        except Exception as e:
            log.error("oss put_object_from_file file={} failed, error={}".format(oss_filename, e))

    def generate_signed_url(self, oss_filename, valid_time):
        oss_file_url = self.bucket.sign_url('GET', oss_filename, valid_time)
        return oss_file_url


oss_client = OssClient()
