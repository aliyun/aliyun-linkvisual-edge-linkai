# -*- coding: UTF-8 -*-
import importlib.util
import logging
from linkai import conf
import sys
import os

log = logging.getLogger(__name__)


class AlgorithmManager:
    def __init__(self):
        self.path = conf.get_string("Default", "algoModuleDir")
        self.dict_modules = {}
        self.dict_single_modules = {}
        # self.dict_module_info = {}
        return

    def check_algorithm(self, name):
        if os.path.exists(self.path + "/" + name):
            return True
        return False

    def create_algorithm(self, name, param=None, version=None):
        try:
            if name in self.dict_modules:
                (module, _) = self.dict_modules[name]
            else:
                # module_spec = importlib.util.spec_from_file_location("model", self.path + "/" + name + "/model.py")
                sys.path.append(self.path + "/" + name)
                # print(sys.path)
                module_spec = importlib.util.spec_from_file_location(name, self.path + "/" + name + "/model.py")
                module = importlib.util.module_from_spec(module_spec)
                module_spec.loader.exec_module(module)
                sys.path.pop()
                # print(sys.path)

                info = module.register()
                self.dict_modules[name] = (module, info)

            # 动态加载 算法模型
            return module.Model()
        except Exception as e:
            log.error(e, exc_info=True)

    def create_algorithm_with_single(self, name, version=None):
        if name in self.dict_single_modules:
            module = self.dict_single_modules[name]
        else:
            module = self.create_algorithm(name)
            self.dict_single_modules[name] = module
        return module

    def get_algo_info(self, name):
        info = {}
        if name in self.dict_modules:
            (_, info) = self.dict_modules[name]
        return info


algo_manager = AlgorithmManager()
