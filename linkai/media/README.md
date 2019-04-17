
1. avi转mp4
ffmpeg -i tyl.avi -c:v libx264 -crf 19 -preset slow -c:a aac -b:a 192k -ac 2 tyl.mp4


2. rtmp h264解码
gst-launch-1.0 -v rtmpsrc location=rtmp://192.168.31.180:1935/stream/zhouhao ! flvdemux ! h264parse ! video/x-h264, stream-format=byte-stream ! filesink location="bbb.h264"

3. h264转mp4
ffmpeg -framerate 25 -i bbb.h264 -c:v copy -f mp4 bbb.mp4

4. tee分流器
gst-launch-1.0 -v rtspsrc user-id="admin" user-pw="12345678edcba" location="rtsp://192.168.31.67:554/cam/realmonitor?channel=1&subtype=0" latency=0 ! tee name=t \
t. ! queue ! rtph264depay ! h264parse ! avdec_h264 ! autovideosink \
t. ! queue ! rtph264depay ! h264parse ! avdec_h264 ! filesink location=./test.mp4

5. 推流
ffmpeg -re -i /Users/qq474536918/Downloads/dianshi_192_168_1_195_2018_09_11_11_00_47.mp4 -vcodec copy -acodec aac -ar 44100 -f flv rtmp://192.168.31.180:1935/stream/zhouhao
ffmpeg -re -i /Users/qq474536918/Downloads/tyl2.mp4 -vcodec copy -acodec aac -ar 44100 -f flv rtmp://192.168.31.180:1935/stream/zhouhao


6. 去掉音频保留视频
ffmpeg -tyl.mp4 -vcodec copy –an  tyl2.mp4


7. resp server
7.1 tar xf gst-rtsp-server-1.14.3.tar.xz
7.2 cd gst-rtsp-server-1.14.3
7.3 ./configure
7.4 cd examples
7.5 修改test-mp4.c  
str = g_strdup_printf (
      "("
      " filesrc location=\"%s\" ! qtdemux "
      " !queue ! h264parse ! rtph264pay pt=96 name=pay0 "
      ")", argv[1]);
7.6 cd ..
7.7 make -j8
7.8 cd examples
7.9 ./test-mp4 mg.mp4