# -*- coding: UTF-8 -*-
from read_version import read_version
from setuptools import setup, find_packages
NAME = "linkai"
PACKAGES = [NAME] + ["%s.%s" % (NAME, i) for i in find_packages(NAME)]
print(PACKAGES)
setup(
    name="linkai",
    version=read_version("linkai", "__init__.py"),
    description="Link AI Node",
    long_description=open("README.md", encoding='utf-8').read(),
    author="aliyun-iot",
    author_email="iot.aliyun.com",
    url="",
    license="",
    package_dat="Default.cfg",
    include_package_data=True,  # 主动打包文件夹内所有数据
    packages=PACKAGES,
    test_suite="linkai/tests",
    # 这里添加依赖项
    install_requires=[
        'PyGObject==3.30.1',  # GSTREAMER 依赖库
        'numpy==1.15.2',
        'Flask==1.0.2',  # 网络框架
        'tensorflow==2.9.3',  # 算法框架
        'Pillow==5.3.0',
        'oss2==2.6.0',
        'redis==3.0.1',
        'psutil==5.4.8',
        'pika==0.12.0',
        'opencv-python==3.4.3.18',
        'ffmpy==0.2.2',
        'paho-mqtt==1.4.0',
    ],
    entry_points={
        'console_scripts': [
            "linkai=linkai.main:main",
        ], },
)
