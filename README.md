# 算法容器

1.支持动态加载TensorFlow模型,openvino模型  
2.支持RTSP/RTMP/本地视频解码  
3.支持Intel集显硬解码 NvidiaGPU 硬解码  
4.支持API 接口调用  


# 安装环境、启动命令等
2.1 环境准备和运行

创建venv环境  
pip3 install virtualenv    
virtualenv --no-site-packages venv  
source venv/bin/activate 

安装依赖库   
pip3 install -r requirements.txt -i  https://mirrors.aliyun.com/pypi/simple/ 

指定连接云端设备三元组信息  
在根目录下的Default.cfg中填入  
product_key =  
device_name =  
device_secret =

创建算法模型目录和logs目录  
mkdir algomodule  
mkdir logs  

打包  
python3 setup.py develop

当上述命令执行成功后，在当前目录下执行：  
linkai -l

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







# 代码目录结构说明，更详细点可以说明软件的基本原理
```
.
├── linkai
    ├── algo_result.py  算法类型定义模块
    ├── algostore.py    算法加载模块
    ├── conf.py         配置读取模块
    ├── main.py         代码执行入口
    ├── algo_oam        算法模型增删改查模块
    ├── linkkit         连接阿里云模块
    ├── media           流媒体接入模块
    ├── oss             录像存储
    ├── service         API接口
    ├── task            任务
    └── utils           工具模块

```


# 常见问题说明