# 算法容器

1.支持动态加载TensorFlow模型,openvino模型  
2.支持RTSP/RTMP/本地视频解码  
3.支持Intel集显硬解码 NvidiaGPU 硬解码  
4.支持API 接口调用  


# 安装环境、启动命令等。
2.1 制作安装包  
python3 setup.py bdist_egg  
会在dist/ 目录下生成一个 linkai-0.9.0-py3.6.egg 的安装包  

2.2 在生产环境部署安装包  
将linkai-0.9.0-py3.6.egg 拷贝到生产环境上  
运行  
easy_install linkai-0.9.0-py3.6.egg  
会开始安装  
安装好后运行 linkai 就能启动程序  
运行目录如下：  
需要包含配置文件和模块目录  
```
.
├── Default.cfg
└── algomodule
    └─── humandetect
        ├── frozen_inference_graph.pb
        └── model.py
```




# 简要的使用说明。
创建venv环境  
pip3 install virtualenv  
mkdir myapp  
cd myapp  
virtualenv --no-site-packages venv  
source venv/bin/activate  

myapp目录就是一个干净的python 环境  
可以在下面运行  
easy_install linkai-0.9.0-py3.6.egg  


# 代码目录结构说明，更详细点可以说明软件的基本原理。
```
.
├── linkai
    ├── algostore.py    算法加载模块
    ├── conf.py         配置读取模块
    ├── main.py
    ├── media           流媒体接入模块
    ├── oss             录像存储
    ├── service         API接口
    ├── task            任务
    ├── utils

```

# 架构图

# 常见问题说明。