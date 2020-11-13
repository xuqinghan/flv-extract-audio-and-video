'''
1 pyav的frame切分 和 每秒钟sample无关!
对wav 1个frame 是 2048个int16  相当于每个channel 1024个sample byte 4096，
但1秒钟的sample_rate是44100个, byte_rate 176400

5 pvav提供了Audio FIFOs   write 端是 frame，  read 端是sample 很好
   应该用多线程

2 wav文件由chunk组成https://www.jianshu.com/p/9fdc0eaa2dea
结果发现混入了1个LIST chunk，没有从data开始播放，导致下午一直播放有杂音

解决思路，用wave.open(filename_audio, "rb") as f:
        #str_data = f.readframes(nframes)
这样用simpleaudio的         
play_obj = sa.play_buffer(wave_data, num_channels, 2, 44100)
播放是没有问题的，说明data找对了。
然后才发现的这个问题
一定要找对正确的基准

3 每次读出的buffer不能太小，最好是1秒钟的。 

4 播放很卡， 应该用多线程




'''


import av
import simpleaudio as sa
#from pydub import AudioSegment
#from pydub.playback import play
import time
import wave  
import numpy as np
import struct

#filename_aac = 'xb2_kos.aac'
#filename_audio = 'D:/dataset/多瑙河之波.aac'
filename_audio = 'D:/dataset/多瑙河之波.wav'
#wav
# [[ 49  49  54 ... -13   1   1]] (1, 2048)
# [[ 15  15  23 ... -55 -54 -54]] (1, 2048)
# [[-61 -61 -70 ... -13  -2  -2]] (1, 2048)
# [[ 10  10  18 ... -49 -57 -57]] (1, 2048)
# [[-63 -63 -65 ... -33 -38 -38]] (1, 2048)
# [[-35 -35 -28 ...  46  46  46]] (1, 2048)
# [[47 47 49 ... 29 33 33]] (1, 2048)
# [[30 30 22 ... 10 17 17]] (1, 2048)

# with av.open(filename_audio) as container:

#     # for index, stream in enumerate(container.streams):
#     #     print(index, stream)
#     #print(container.streams)
#     stream = container.streams.get(audio=0)
#     stream1 = container.streams

#     for frame in container.decode(stream):
#         #print(frame.planes)
#         #decoded_data = frame.planes[0].to_bytes()
#         frame_np = frame.to_ndarray()
#         #print(frame_np, frame_np.shape)
#         #frame_np2 = frame_np.reshape(1024,)
#         #print(frame_np2)
#         play_obj = sa.play_buffer(frame_np, 2, 2, 44100)
#         #play_obj = sa.play_buffer(frame_np, 2, 2, 44100)
#         #play_obj.wait_done()
#         #break
#         time.sleep(0.0001)

#parse WAV !  混入LIST chunk 导致之前一直有杂音！

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




with open(filename_audio, 'rb') as f:
#with wave.open(filename_audio, "rb") as f:
    #params = f.getparams()  
    #nchannels, sampwidth, framerate, nframes = params[:4]
    #print(nchannels, sampwidth, framerate, nframes)
    num_channels, BytsPerSample, sample_rate, byte_rate = read_header_wav(f)

    while f:
        #print('play')
        #str_data = f.readframes(nframes)
        str_data = f.read(byte_rate*10) # 176400
        #print(str_data)
        wave_data = np.frombuffer(str_data, dtype=np.int16)
        #print(wave_data)
        # wave_data.shape = -1,2
        # #转置数据
        # wave_data = wave_data.T
        # print(wave_data)
        #b = f.read(176400)
        #b = f.read(44100)
        play_obj = sa.play_buffer(wave_data, num_channels, BytsPerSample, sample_rate)
        play_obj.wait_done()
        #time.sleep(5)
        #break

# sound = AudioSegment.from_file(filename_audio, format="wav")
# # print(sound)
# # sound = sound[0:1024]
# # play(sound)

# for i in range(100):
#     # 4096 速度最正确
#     samples = sound[i*4096:(i+1)*4096].get_array_of_samples()
#     print(samples)
#     print(len(samples))
#     new_sound = sound._spawn(samples)
#     play(new_sound)

    