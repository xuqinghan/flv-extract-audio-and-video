'''
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
import numpy as np
#import cv2
from datetime import datetime

from pathlib import Path
import asyncio
import time
#import u_image

import rx
from rx import of, operators as ops
from rx.subject import Subject

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


async def mock_live_flv_round1(path_to_video, id_vehicle, event_live_end, sender):
    '''
        模拟直播1轮视频文件，用pts作为延迟，模拟直播速度
        每次 pts从0开始 
    '''
    #异步模式下卡死？
    #while True:
    #模拟直播开始
    container = av.open(str(path_to_video))

    print('打开了视频', path_to_video)
    #i = 0
    pts = 0 
    #时间戳 每次播放的0时刻，后面用pts作为偏移，用于对齐音视频？
    #ts_0 = datetime.now().timestamp()

    elapse = 0.01
    #ts_decoder_start = time.monotonic()

    for frame in container.decode(video=0, audio=0):
        if event_live_end.is_set():
            #停止直播，退出
            return

        kind = 'aac' if isinstance(frame, av.AudioFrame) else 'h264'
        sender(kind, frame)
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

class SaverMock:
    def __init__(self, event_need_record):
        self.event_need_record = event_need_record
        self.is_recording = False
        self.container = None
        self.stream_video = None
        self.stream_audio = None
        

    def on_frame(self, args):
        #print(self, args)
        if self.event_need_record.is_set():
            event, frame = args
            if self.is_recording:
                print('模拟收到，保存', event, frame)

                if event == 'h264':
                    for packet in self.stream_video.encode(frame):
                        self.container.mux(packet)
                elif event == 'aac':
                    pass
            else:
                #没开始保存
                if event == 'h264':
                    self.start(frame)
        else:
            if self.is_recording:
                self.is_recording = False
                print('停止录像')
                self.end()
            else:
                #停止中
                pass

    def start(self, frame_video):
        print('开始录像')
        self.is_recording = True
        print(frame_video.width, frame_video.height, frame_video.format.name)
        self.container = av.open(f'{datetime.now().isoformat()}.mp4', mode='w')
        fps = 24
        self.stream_video = self.container.add_stream('h264', rate=fps)
        self.stream_video.width = frame_video.width
        self.stream_video.height = frame_video.height
        #self.stream_video.pix_fmt = 'yuv420p'
        self.stream_video.pix_fmt = frame_video.format.name

    def end(self):
        # Flush stream
        for packet in self.stream_video.encode():
            self.container.mux(packet)

        # Close the file
        self.container.close()


async def main(event_loop):
    #主循环不退出
    co1 = mock_live_flv_round1(path_to_video, id_vehicle, event_live_end, sender_mock)
    #event_loop.create_task()
    #创建event_loop
    co2 = client_mock()
    #print(co1)
    task1 = event_loop.create_task(co1)
    task2 = event_loop.create_task(co2)
    await task1
    await task2
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

    def sender_mock(event, data):
        #print('模拟发送走', event, data)
        video_subject.on_next((event, data))

    saver = SaverMock(event_need_record)

    #C之后增加D
    video_subject.subscribe(lambda args: saver.on_frame(args))

    async def client_mock():
        '''模拟客户操作，直播开始30秒后开始录像 30秒后停止录像'''
        print('客户操作')
        await asyncio.sleep(3)
        print('模拟玩家开始直播')
        event_need_record._loop.call_soon_threadsafe(event_need_record.set)
        await asyncio.sleep(20)
        print('模拟玩家停止直播')
        event_need_record._loop.call_soon_threadsafe(event_need_record.clear)


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


