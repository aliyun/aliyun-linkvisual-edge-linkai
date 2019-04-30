# 算法容器

1.支持动态加载TensorFlow模型,openvino模型  
2.支持RTSP/RTMP/本地视频解码  
3.支持Intel集显硬解码 NvidiaGPU 硬解码  
4.支持API 接口调用  


# 安装环境、启动命令等
2.1 环境准备和运行

2.1.1 创建venv环境  
pip3 install virtualenv    
virtualenv --no-site-packages venv  
source venv/bin/activate 

2.1.2 安装依赖库   
pip3 install -r requirements.txt -i  https://mirrors.aliyun.com/pypi/simple/ 

2.1.3 指定连接云端设备三元组信息  
在根目录下的Default.cfg中填入  
product_key =  
device_name =  
device_secret =

2.1.4 创建logs目录  
mkdir logs  

2.1.5 打包  
python3 setup.py develop

2.1.6 程序执行  
linkai -l

# 视频推理
2.2 边缘智能视频分析  
当程序运行后，需要使用阿里云智能视频服务下发算法模型到algomodule目录下  
并使用阿里云的相关的云端服务开启和停止算法任务，详情请参见阿里云官网的LinkVisual服务

# 代码目录结构说明
```
.
├── algomodule    
    ├── age_gender_recognition  算法模型示例
├── linkai
    ├── algo_result.py          算法类型定义模块
    ├── algostore.py            算法加载模块
    ├── conf.py                 配置读取模块
    ├── main.py                 代码执行入口
    ├── algo_oam                算法模型增删改查模块
    ├── linkkit                 连接阿里云套件模块
    ├── media                   流媒体接入模块
    ├── oss                     对象存储服务模块
    ├── service                 API接口
    ├── task                    任务模块
    └── utils                   工具模块
├── Default.cfg                 默认配置文件
├── README.md                   readme文件
├── log.conf                    log信息文件
├── model.json                  物模型文件
├── requirements.txt            程序运行的依赖库文件
└── setup.py                    打包setup文件
```

# 常见问题说明