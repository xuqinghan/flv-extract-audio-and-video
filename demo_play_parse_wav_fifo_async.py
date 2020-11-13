import aiofiles
import asyncio
import simpleaudio as sa
import numpy as np
import struct
from datetime import datetime 
import av
from av.audio.fifo import AudioFifo

'''
    卡顿原因 读取 io操作会导致进程卡住，所以必须异步化
    测试AudioFifo
'''


async def read_header_wav_async(f):
    #RIFF
    await f.read(12)
    #FORMAT
    id_chunk = await f.read(4)
    s = await f.read(4)
    size_chunk, *_ = struct.unpack('<I', s)
    print(id_chunk, size_chunk)
    s = await f.read(16)
    audio_format, num_channels, sample_rate, byte_rate, BlockAlign, BitsPerSample = struct.unpack('<hhIIhh',s)
    print(audio_format, num_channels, sample_rate, byte_rate, BlockAlign, BitsPerSample)
    #DATA?
    #LIST?!
    #不能是True！
    while id_chunk != b'data':
        id_chunk = await f.read(4)
        # 26
        s = await f.read(4)
        size_chunk, *_ = struct.unpack('<I',s)
        print(id_chunk, size_chunk)
        if id_chunk != b'data':
            await f.read(size_chunk)
        else:
            break

    print(id_chunk, size_chunk)

    return num_channels, int(BitsPerSample/8), sample_rate, byte_rate


def read_header_wav(f):
    #RIFF
    f.read(12)
    #FORMAT
    b = f.read(4)
    size_chunk, *_ = struct.unpack('<I',f.read(4))
    print(b, size_chunk)
    audio_format, num_channels, sample_rate, byte_rate, BlockAlign, BitsPerSample = struct.unpack('<hhIIhh',f.read(16))
    print(audio_format, num_channels, sample_rate, byte_rate, BlockAlign, BitsPerSample)
    #DATA?
    #LIST?!
    while True:
        id_chunk = f.read(4)
        # 26
        size_chunk, *_ = struct.unpack('<I',f.read(4))
        print(id_chunk, size_chunk)
        if id_chunk != b'data':
            f.read(size_chunk)
        else:
            break
            print(b, size_chunk)

    return num_channels, int(BitsPerSample/8), sample_rate, byte_rate



async def parser(event_end_parse, filename_audio, audio_fifo, sample_per_frame, sample_rate):
    '''懒惰的生产者，只管延时接受，不管其他'''
    #生产每frame需要的时间
    sec_per_frame = sample_per_frame/sample_rate
    with av.open(filename_audio) as container:
        stream = container.streams.get(audio=0)
        for frame in container.decode(stream):
            await asyncio.sleep(sec_per_frame*0.95)
            audio_fifo.write(frame)
            #print('parser: add data to queue')
    
    print('结束产生')
    #通知客户端结束
    event_end_parse.set()    

async def player(event_end_parse, event_end_play, audio_fifo, num_channels, BytsPerSample, sample_rate, sec_play:int):
    '''只等待'''
    samples_play_once = sample_rate*sec_play
    event_played_frame1 = asyncio.Event()
    first = True
    data_wait_play = None
    while True:
        #print('player')
        if event_end_parse.is_set() and audio_fifo.samples < samples_play_once:
            #没数据了，就通知
            break
        
        #---------读数据-----------
        #print('player 等待读取 队列中样本数', audio_fifo.samples)
        if data_wait_play is None:
            if audio_fifo.samples >= samples_play_once:
                print('player 开始读取', samples_play_once, sec_play)
                frame = audio_fifo.read(samples_play_once)
                print('player: get data from queue')
                data_wait_play = frame.planes[0].to_bytes()
            else:
                await asyncio.sleep(0.001)
        #     #n_sample = audio_fifo.samples
        #     #if n_sample >= samples_play_once:
        #         #sec_play_real = n_sample/samples_play_once
        #         #按样本数*播放秒数读取

        #         #frame_np = frame.to_ndarray()
        #         #print(frame_np, frame_np.shape)
        #         #data_bytes = await queue.get()
        else:
            #-----------播放 不能太快播放-------------
            if first:
                first = False
            else:
                await event_played_frame1.wait()
            print('player: start play', datetime.now())
            play_obj = sa.play_buffer(data_wait_play, num_channels, BytsPerSample, sample_rate)
            #按播放秒数等待
            data_wait_play = None
            #play_obj.wait_done()
            await asyncio.sleep(sec_play)
            #通知播放完毕可以继续播放下一个frame了
            event_played_frame1.set()
            print('player: end play', datetime.now())
            
        
 
    print('player 退出')
    event_end_play.set()

# async def player(event_end_parse, event_end_play, audio_fifo, num_channels, BytsPerSample, sample_rate, sec_play:int):
#     '''只等待'''
#     samples_play_once = sample_rate*sec_play
#     event_played_frame1 = asyncio.Event()
#     first = True
#     data_wait_play = None
#     while True:
#         #print('player')
#         if event_end_parse.is_set() and audio_fifo.samples < samples_play_once:
#             #没数据了，就通知
#             break
        
#         #---------读数据-----------
#         #print('player 等待读取 队列中样本数', audio_fifo.samples)

#         print('player 开始读取', samples_play_once, sec_play)
#         frame = audio_fifo.read(samples_play_once)
#         print('player: get data from queue')
#         data_wait_play = frame.planes[0].to_bytes()

#         print('player: start play', datetime.now())
#         play_obj = sa.play_buffer(data_wait_play, num_channels, BytsPerSample, sample_rate)
#         #play_obj.wait_done()
#         await asyncio.sleep(sec_play)
#         #通知播放完毕可以继续播放下一个frame了
#         print('player: end play', datetime.now())
#         await asyncio.sleep(0.001)
        
 
#     print('player 退出')
#     event_end_play.set()



async def main(event_loop, filename_audio, sec_play:int):
    #queue = asyncio.Queue()
    audio_fifo = AudioFifo()
    event_end_parse = asyncio.Event()
    event_end_play = asyncio.Event()
    #f = await aiofiles.open(filename_audio, 'rb')
    #只用来读参数
    with open(filename_audio, 'rb') as f:
        num_channels, BytsPerSample, sample_rate, byte_rate = read_header_wav(f)
    #简单启动2个coroutine 不能await
    sample_per_frame = 1024
    coroutine1 = parser(event_end_parse, filename_audio, audio_fifo, sample_per_frame, sample_rate)
    task1 = event_loop.create_task(coroutine1)
    coroutine2 = player(event_end_parse, event_end_play, audio_fifo, num_channels, BytsPerSample, sample_rate, sec_play)
    task2 = event_loop.create_task(coroutine2)
    #等待结束
    #print('结束')
    await event_end_play.wait()

    # data_bytes = None
    # is_playing = False
    # while f:
    #     if data_bytes is None:
    #         print('parser: begin parse')
    #         data_bytes = await f.read(byte_rate*sec_play) # 176400
    #         print('parser: add data to queue')
    #     else:
    #         #not None
    #         if is_playing:
    #             pass
    #         else:
    #             is_playing = True
    #             print('player: get data from queue')
    #             play_obj = sa.play_buffer(data_bytes, num_channels, BytsPerSample, sample_rate)
    #             data_bytes = None
    #             print('player: start play ')
    #             await asyncio.sleep(sec_play)
    #             print('player: end play')
    #             is_playing = False
        #await asyncio.sleep(0.01)




if __name__ == "__main__":
    filename_audio = 'D:/dataset/多瑙河之波.wav'
    sec_play = 5

    event_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(event_loop)

    try:
        event_loop.run_until_complete(main(event_loop, filename_audio, sec_play))
    except KeyboardInterrupt:
        '''按键退出'''
        pass
        #now = event_loop.time()
        # print(asyncio.Task.all_tasks())

    event_loop.close()
