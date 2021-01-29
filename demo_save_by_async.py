'''

20210128

数据源直接用pyav的frame。

验证pyav保存+rx+asynic


如果在界面中保存，同样有这个问题，但是不影响，可以正常保存
specified frame type (3) at 0 is not compatible with keyframe interval


按frame打开数据源 解码为frame
按frame保存 + 异步


根据异步event判断 做什么： 

收到event
1开始录制。 初始化视频大小？数据源提前初始化好音视频初始header？
2 结束录制

pts 20秒附近
录像机开始1个新录像
保存图像 <av.VideoFrame #259, pts=17290 yuv420p 384x288 at 0x253c2b06280>
实际保存 视频帧 <av.VideoFrame #259, pts=0 yuv420p 384x288 at 0x253c2b06280> time = 0.0 pts=0 time_base=1/1000
直播中
解码结果 aac <av.AudioFrame 745, pts=17298, 1024 samples at 44100Hz, stereo, fltp at 0x253c2ad4ba0>
保存音频 <av.AudioFrame 745, pts=17298, 1024 samples at 44100Hz, stereo, fltp at 0x253c2ad4ba0>
直播中
解码结果 aac <av.AudioFrame 746, pts=17321, 1024 samples at 44100Hz, stereo, fltp at 0x253c2ad4dd0>
保存音频 <av.AudioFrame 746, pts=17321, 1024 samples at 44100Hz, stereo, fltp at 0x253c2ad4dd0>
直播中
解码结果 aac <av.AudioFrame 747, pts=17344, 1024 samples at 44100Hz, stereo, fltp at 0x253c2fb5430>
保存音频 <av.AudioFrame 747, pts=17344, 1024 samples at 44100Hz, stereo, fltp at 0x253c2fb5430>
直播中
解码结果 h264 <av.VideoFrame #260, pts=17356 yuv420p 384x288 at 0x253c2b06100>
保存图像 <av.VideoFrame #260, pts=17356 yuv420p 384x288 at 0x253c2b06100>
实际保存 视频帧 <av.VideoFrame #260, pts=66 yuv420p 384x288 at 0x253c2b06100> time = 0.066 pts=66 time_base=1/1000
发出
1 视频header， 音频header
2 视频帧
3 音频帧

'''
import av
#from av.video.frame import VideoFrame

import numpy as np
import cv2
from datetime import datetime

from pathlib import Path
import asyncio
import time

import rx
from rx import of, operators as ops
from rx.subject import Subject

from u_save_video import Recorder


# def get_data_bytes_aac(frame):
#     '''转int16'''
#     #nparray
#     ndarray = frame.to_ndarray()
#     #print(array)
#     #print(array.shape)
#     #bytes .tostring()
#     return ndarray.tobytes()

# def get_data_bytes_h264(frame):
#     #PIL格式
#     img_pil = frame.to_image()
#     #opencv格式
#     img_cv = cv2.cvtColor(np.asarray(img_pil),cv2.COLOR_RGB2BGR)
#     #jpg编码
#     return u_image.img2bytes_jpg(img_cv)

# frame2databytes = {'aac': get_data_bytes_aac, 'h264': get_data_bytes_h264}

# #aac
# sampleNumber = 1024
# sampleRate = 44100
# elaspe_aac_package = sampleNumber/sampleRate



async def mock_live_flv_round1(path_to_video, id_vehicle, event_live_end, event_need_record, sender):
    '''
        模拟直播1轮视频文件，用pts作为延迟，模拟直播速度
        每次 pts从0开始 
    '''
    #异步模式下卡死？
    #while True:
    #模拟直播开始
    #container = av.open(str(path_to_video))
    container = av.open(path_to_video, mode='r')


    print('打开了视频', path_to_video)
    #i = 0
    pts = 0 
    #时间戳 每次播放的0时刻，后面用pts作为偏移，用于对齐音视频？
    #ts_0 = datetime.now().timestamp()

    elapse = 0.01
    #container_out = None
    #recorder = Recorder(id_vehicle, event_need_record)
    #ts_decoder_start = time.monotonic()
    #pts_save_t0 = 0


    for frame in container.decode(video=0, audio=0):
        stream_video_in = container.streams.video[0]
        #print('time_base', stream_video_in.time_base)
        if event_live_end.is_set():
            #停止直播，退出
            break
        print('直播中')
        kind = 'aac' if isinstance(frame, av.AudioFrame) else 'h264'
        print('解码结果', kind, frame)
        sender(kind, frame)

        await asyncio.sleep(elapse)




def show_frame264(frame):

    img = frame.to_image()
    #opencv格式
    img = cv2.cvtColor(np.asarray(img),cv2.COLOR_RGB2BGR)
    #print(img)
    cv2.imshow("h264", img)
    k = cv2.waitKey(1)



    # while True:
    #     await asyncio.sleep(1)

if __name__ == '__main__':
    #直播结束，如果设置，则结束直播
    event_live_end = asyncio.Event()
    #录制，如果set，则需要发送走
    event_need_record = asyncio.Event()
    id_vehicle = '1'
    #LiveInside('1', )
    #print(data_bytes)

    path_to_video = Path('D:/xqh/4dev/zgy/data-origin/inside', '多瑙河之波-手风琴.flv')

    video_subject = Subject()

    def sender(kind, data):
        #print('模拟发送走', event, data)
        video_subject.on_next((kind, data))


    #-----保存录像----------
    def fname_record1():
        #f'{datetime.now().isoformat()}'
        dt_str = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
        return f'{id_vehicle}_{dt_str}'


    #订阅
    # ----------保存----------
    recorder = Recorder(fname_record1, event_need_record)
    video_subject.subscribe(lambda args: recorder.on_frame(*args))

    #----------播放-----------
    video_subject.pipe(
        #处理：过滤出图像
        ops.filter(lambda args: args[0] == 'h264')
        #过滤出frame部分
        ,ops.map(lambda args: args[1])
    ).subscribe(show_frame264)

    async def client_mock():
        '''模拟客户操作，直播开始30秒后开始录像 30秒后停止录像'''
        print('客户操作')
        await asyncio.sleep(20)
        print('模拟玩家开始录像')
        event_need_record._loop.call_soon_threadsafe(event_need_record.set)
        await asyncio.sleep(30)
        print('模拟玩家停止图像')
        event_need_record._loop.call_soon_threadsafe(event_need_record.clear)
        await asyncio.sleep(10)
        print('模拟玩家停止直播')
        event_need_record._loop.call_soon_threadsafe(event_live_end.set)

    async def main(event_loop):
        #主循环不退出
        co1 = mock_live_flv_round1(str(path_to_video), id_vehicle, event_live_end, event_need_record, sender)
        #event_loop.create_task()
        #创建event_loop
        co2 = client_mock()
        #print(co1)
        task1 = event_loop.create_task(co1)
        task2 = event_loop.create_task(co2)
        await task1
        await task2



    event_loop = asyncio.get_event_loop()
    #event_loop = asyncio.new_event_loop()
    #asyncio.set_event_loop(event_loop)

    try:
        event_loop.run_until_complete(main(event_loop))
        #asyncio.run(main(event_loop))
    except KeyboardInterrupt:
        '''按键退出'''
        #now = event_loop.time()
        # print(asyncio.Task.all_tasks())

    event_loop.close()


