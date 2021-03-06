'''
h264解码器需要的额外信息  实测就是h264 header部分的数据
https://github.com/PyAV-Org/PyAV/pull/287


'''
import copy
import av
from av.bytesource import ByteSource

container = av.open('xb2_kos.flv')

# Find index of the video stream 
video_stream_index = 0
for index, stream in enumerate(container.streams):
    if isinstance(stream, av.video.stream.VideoStream):
        video_stream_index = index
        break

print('video_stream_index', video_stream_index)

codec_name = container.streams[video_stream_index].codec_context.name
print('codec_name', codec_name)
codec_origin = container.streams[video_stream_index].codec_context
extradata = codec_origin.extradata

#bytes
print('extradata', extradata)


codec_new = av.codec.CodecContext.create(codec_name, 'r')
codec_new.extradata = extradata

with open('./dumps/h264_extradata.dump', 'wb') as f:
    f.write(extradata)

print(extradata)
with open('./dumps/h264_extradata.dump', 'rb') as f:
    extradata2 = f.read()
print(extradata2)

# exit code 3221226356
#codec_new.extradata = extradata2
codec_new.extradata = copy.deepcopy(extradata)
#codec_new.extradata = ByteSource(extradata2)
