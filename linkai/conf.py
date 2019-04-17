# -*- coding: UTF-8 -*-
import configparser

conf = configparser.ConfigParser()


def get_string(section, key):
    conf.read("Default.cfg", "utf-8")
    return conf.get(section, key)


def get_int(section, key):
    conf.read("Default.cfg", "utf-8")
    return conf.getint(section, key)


def get_float(section, key):
    conf.read("Default.cfg", "utf-8")
    return conf.getfloat(section, key)
