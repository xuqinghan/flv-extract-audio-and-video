# 
原版是分别解出了aac和h264裸流，直接写到文件里

现在希望 得到aac和h264之后，归于pyav的frame！

1 生产端 如何把各帧转变为pyav的frame？

2 消费端 如何用pyav保存为 音视频混流的 mp4？

——破题，从消费端入手


# flv-extract-audio-and-video
Extract the .acc audio and .h264 video from the flv video.

# introduction
This project is used to extract .aac audio file from the flv video and only .acc audio in the flv video supported. It works well on bilibili video.

# usage
for example

./extract.py -i xb2_kos.flv -o xb2_kos.aac

./extract.py -i xb2_kos.flv -o xb2_kos.h264
# todo
//maybe add video extract support.

added