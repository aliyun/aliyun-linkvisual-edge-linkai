# -*- coding: UTF-8 -*-
from linkai.media.manager import media_manager
from linkai.service.service import app
from linkai import conf
import logging as log
import logging.config

import importlib.util
from argparse import ArgumentParser
import signal
import os


signal.signal(signal.SIGINT, signal.SIG_DFL)  # 保证Ctrl+C 时程序正常结束

if os.path.isfile("log.conf"):
    logging.config.fileConfig('log.conf')
else:
    log.basicConfig(level=log.INFO)

if "HTTP_PORT" in os.environ:
    http_port = os.environ["HTTP_PORT"]
else:
    http_port = conf.get_int("Default", "httpPort")


def build_arg_parser():
    parser = ArgumentParser()
    parser.add_argument("-l", "--linkkit", help="开启linkkit上行通道", action='store_true')
    return parser


def main():
    args = build_arg_parser().parse_args()
    media_manager.gst_bus_loop_start()

    log.info("Start Link AI")

    if args.linkkit or "LINK_KIT" in os.environ:
        adapter_path = os.path.split(__file__)[0] + "/linkkit/linkkit_adapter.py"
        module_spec = importlib.util.spec_from_file_location("linkkit_adapter", adapter_path)
        adapter_module = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(adapter_module)

    app.run(host='0.0.0.0', port=http_port, threaded=False, processes=1)
    log.info("Stop Link AI")


if __name__ == '__main__':
    main()
