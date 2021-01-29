'''

20210128

如果在界面中保存，同样有这个问题，但是不影响，可以正常保存
specified frame type (3) at 0 is not compatible with keyframe interval


按frame打开数据源 解码为frame
按frame保存 + 异步


根据异步event判断 做什么： 

收到event
1开始录制。 初始化视频大小？数据源提前初始化好音视频初始header？
2 结束录制




发出
1 视频header， 音频header
2 视频帧
3 音频帧

'''
import av
#from av.video.frame import VideoFrame

import numpy as np
#import cv2
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
        #print('发送走', frame)
        sender(frame)
        #只能在这里录制，rx订阅报错
        #recorder.on_frame(frame)
        # if kind == 'h264':
        #     #img = frame.to_image()


        # if event_need_record.is_set():
        #     #录制
        #     if record1_video is None:
        #         record1_video = RecordVideo(frame.pts, frame.width, frame.height)
        #         # container_out = av.open('test111.mp4', mode='w')
        #         # stream_video = container_out.add_stream('h264', rate=24)
        #         # #stream_video.time_base = Fraction(1, 48000)
        #         # stream_video.time_base = stream_video_in.time_base
        #         # stream_video.width = 384
        #         # stream_video.height = 288
        #         # stream_video.pix_fmt = 'yuv420p'
        #         # stream_audio = container_out.add_stream('aac', rate=44100)
                

        #     # print('偏移前', frame.pts, frame.dts, frame.pts)

        #     # print('偏移后', frame.pts, frame.dts, frame.pts)
        #     #print('stream time_base', stream_video.time_base)
        #     #print()
        #     if kind == 'h264':
        #         # packets = stream_video.encode(frame)
        #         # print(packets)
        #         # for packet in packets:
        #         #     container_out.mux(packet)
        #         record1_video.save_frame1_video(frame)
        #     elif kind == 'aac':
        #         # #清空pts
        #         # frame.pts = None
        #         # for packet in stream_audio.encode(frame):
        #         #     container_out.mux(packet)
        #         record1_video.save_frame1_audio(frame)
        # else:
        #     #停止
        #     if record1_video is not None:
        #         print('停止直播')
        #         record1_video.end()
        #         record1_video = None
        #         # Close the file
        #         #container_out.close()
        #         #container_out = None

        # if i > 100:
        #     break
        #print('pts', frame.pts)
        # elapse_src_sec = (frame.pts - pts)/1e3
        # #更新pts
        # pts = frame.pts
        



        # #秒数
        # ts = ts_0 + pts/1e3
        # #直接以延时后的时间为时间戳
        # #转bytes 用于发送
        # if kind == 'h264':
        #     data_bytes = get_data_bytes_h264(frame)
        # elif kind == 'aac':
        #     data_bytes = get_data_bytes_aac(frame)
        # else:
        #     continue 
            # #声音的话需要知道sapmples 根据这个决定延时
            # array = frame.to_ndarray()
            # #data_bytes  = array.tobytes()
            # data_bytes = array.tolist()
            # n_sample = array.shape[1]
            # elaspe_need = n_sample/sampleRate
            # elapse_src_sec = elaspe_need

        #data_bytes = frame2databytes[kind](frame)
        # event = 'acc_vehicle_inside_captured' if kind == 'aac' else 'img_vehicle_inside_captured'
        # #ts = datetime.now().timestamp()
        # await sender(event, (id_vehicle, ts, data_bytes))

        # #await asyncio.sleep(elapse_src_sec)

        # #gateway事件类型


        # ts_decode_end = time.monotonic()
        # elapse_real_sec = (ts_decode_end - ts_decoder_start)
        # ts_decoder_start = ts_decode_end
        # #发送走
        # #模拟延时
        # #elapse_src_sec = elaspe_aac_package
        # if (elapse_real_sec < elapse_src_sec):
        #     elapse = elapse_src_sec - elapse_real_sec
        # else:
        #     elapse = 0

        #elapse = elapse_src_sec
        #elapse = elaspe_aac_package
        #print(f' {kind} pts={pts}, 编码延时{elapse_src_sec}秒, 解码延时{elapse_real_sec}秒 发送延时{elapse}')

        await asyncio.sleep(elapse)
        #print(kind)
        #i += 1







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

    def sender_mock(data):
        #print('模拟发送走', event, data)
        video_subject.on_next(data)


    #订阅保存
    recorder = Recorder(id_vehicle, event_need_record)
    video_subject.subscribe(lambda frame: recorder.on_frame(frame))

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
        co1 = mock_live_flv_round1(str(path_to_video), id_vehicle, event_live_end, event_need_record, sender_mock)
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


