import threading
import av
from av.audio.fifo import AudioFifo
import time
import simpleaudio as sa
import numpy as np
import struct
from datetime import datetime 

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


class Parser(threading.Thread):
    '''懒惰的生产者，只管延时产生数据，不管其他'''
    def __init__(self, filename_audio,audio_fifo, sample_per_frame, sample_rate):
        threading.Thread.__init__(self)
        self.audio_fifo = audio_fifo
        self.filename_audio = filename_audio
        #生产每frame需要的时间
        self.sec_per_frame = sample_per_frame/sample_rate

    def run(self):
        print ("开始解码线程：" )
        with av.open(filename_audio) as container:
            stream = container.streams.get(audio=0)
            for frame in container.decode(stream):
                #模拟每帧生产，传输时间
                #time.sleep(self.sec_per_frame)
                # if frame.pts == 93:
                #     frame.pts = 92
                frame.pts = None
                self.audio_fifo.write(frame)
                # except ValueError as e:
                #     print(e)
                #     pass

                #print('parser: add data to queue')
    
        print('结束产生 退出解码线程')

class Player(threading.Thread):
    '''从队列读取，不退出！也不考虑读取和播放之间的延迟'''
    def __init__(self, audio_fifo, num_channels, BytsPerSample, sample_rate, sec_play):
        threading.Thread.__init__(self)
        self.audio_fifo = audio_fifo
        self.filename_audio = filename_audio
        self.num_channels = num_channels
        self.BytsPerSample = BytsPerSample
        self.sample_rate = sample_rate
        #每次读取多少样本
        self.samples_play_once = sample_rate*sec_play

    def run(self):
        print ("开始播放器 线程：" )
        while True:
            if self.audio_fifo.samples >= self.samples_play_once:
                print('player: get data from queue')
                frame = self.audio_fifo.read(self.samples_play_once)
                data_wait_play = frame.planes[0].to_bytes()
                print('player: start play', datetime.now())
                play_obj = sa.play_buffer(data_wait_play, self.num_channels, self.BytsPerSample, self.sample_rate)
                play_obj.wait_done()
                print('player: end play', datetime.now())

        print('退出播放器线程')

if __name__ == '__main__':
    #filename_audio = 'D:/dataset/多瑙河之波.wav'
    #num_channels, BytsPerSample, sample_rate = 2, 2, 44100
    #只用来读参数
    # with open(filename_audio, 'rb') as f:
    #     num_channels, BytsPerSample, sample_rate, byte_rate = read_header_wav(f)
    #filename_audio = 'D:/dataset/多瑙河之波.aac'
    #aac 这样对了，但是速度太快 sec_play 要放大 而且采样率也不是44100 48000更合适
    #num_channels, BytsPerSample, sample_rate = 2, 4, 24000
    filename_audio = 'D:/dataset/多瑙河之波-手风琴.flv'
    #frameFrame.pts (93) != expected (92); fix or set to None.
    num_channels, BytsPerSample, sample_rate = 2, 4, 22050

    sec_play = 20
    audio_fifo = AudioFifo()

    #简单启动2个coroutine 不能await
    sample_per_frame = 1024

    # 创建新线程
    parser = Parser(filename_audio, audio_fifo, sample_per_frame, sample_rate)
    player = Player(audio_fifo, num_channels, BytsPerSample, sample_rate, sec_play)

    # 开启新线程
    parser.start()
    player.start()
    #等待解码器结束
    parser.join()
    player.join()
    print ("退出主线程")