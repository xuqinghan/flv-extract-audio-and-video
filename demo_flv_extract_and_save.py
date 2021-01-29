'''
手动解码flv文件
用pvav frame推送保存！

比之前自己写的bitarray解码要精简，单文件完成解码

pts 
开始后20秒大致 
pyav解码播放：
pts=17290

手工解码timestamp

timestamp 4422400   /1000= pts=4422

不对

4422400/17290 = 255.77

20秒附近 手工
模拟玩家开始录像
timestamp 4426240
timestamp 4426240 CompoistionTime=0
直播中
pts 17290.0
解码结果 h264 [<av.VideoFrame #258, pts=17290 yuv420p 384x288 at 0x22efe95de20>]
发送走
录像机开始1个新录像
保存图像 <av.VideoFrame #258, pts=17290 yuv420p 384x288 at 0x22efe95de20>
实际保存 视频帧 <av.VideoFrame #258, pts=0 yuv420p 384x288 at 0x22efe95de20> time = 0.0 pts=0 time_base=1/1000
timestamp 4428288
直播中
pts 17298.0
解码结果 aac [<av.AudioFrame 745, pts=17298, 1024 samples at 44100Hz, stereo, fltp at 0x22efe954dd0>]
发送走
保存音频 <av.AudioFrame 745, pts=17298, 1024 samples at 44100Hz, stereo, fltp at 0x22efe954dd0>
timestamp 4434176
直播中
pts 17321.0
解码结果 aac [<av.AudioFrame 746, pts=17321, 1024 samples at 44100Hz, stereo, fltp at 0x22efe954e40>]
发送走
保存音频 <av.AudioFrame 746, pts=17321, 1024 samples at 44100Hz, stereo, fltp at 0x22efe954e40>
timestamp 4440064
直播中
pts 17344.0
解码结果 aac [<av.AudioFrame 747, pts=17344, 1024 samples at 44100Hz, stereo, fltp at 0x22efec0dc10>]
发送走
保存音频 <av.AudioFrame 747, pts=17344, 1024 samples at 44100Hz, stereo, fltp at 0x22efec0dc10>
timestamp 4443136
timestamp 4443136 CompoistionTime=0
直播中
pts 17356.0
解码结果 h264 [<av.VideoFrame #259, pts=17356 yuv420p 384x288 at 0x22efe95db20>]
发送走
保存图像 <av.VideoFrame #259, pts=17356 yuv420p 384x288 at 0x22efe95db20>
实际保存 视频帧 <av.VideoFrame #259, pts=66 yuv420p 384x288 at 0x22efe95db20> time = 0.066 pts=66 time_base=1/1000




保存音频 <av.AudioFrame 749, pts=17391, 1024 samples at 44100Hz, stereo, fltp at 0x19072af4e40>
保存图像 <av.VideoFrame #260, pts=17423 yuv420p 384x288 at 0x19072afdb20>

pyav 源
录像机开始1个新录像
保存图像 <av.VideoFrame #260, pts=17356 yuv420p 384x288 at 0x2956a285100>
直播中
解码结果 aac <av.AudioFrame 748, pts=17367, 1024 samples at 44100Hz, stereo, fltp at 0x2956a254b30>



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


from parse_flv_file_hard import  parse_stream1
from fractions import Fraction

from u_save_video import Recorder


time_base = Fraction(1, 1000)
time_stamp_f = 256



async def live(fname, event_live_end, sender):
    '''模拟直播'''
    f_stream = open(fname, 'rb')
    await parse_stream1(f_stream, event_live_end, sender,time_base, time_stamp_f)
    f_stream.close()

def show_frame264(frame):

    img = frame.to_image()
    #opencv格式
    img = cv2.cvtColor(np.asarray(img),cv2.COLOR_RGB2BGR)
    #print(img)
    cv2.imshow("h264", img)
    k = cv2.waitKey(1)


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
        return f'手工解码数据源{id_vehicle}_{dt_str}'


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
        print('模拟玩家停止录像')
        event_need_record._loop.call_soon_threadsafe(event_need_record.clear)
        await asyncio.sleep(10)
        print('模拟玩家停止直播')
        event_need_record._loop.call_soon_threadsafe(event_live_end.set)

    async def main(event_loop):
        #主循环不退出
        co1 = live(str(path_to_video), event_live_end, sender)
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
