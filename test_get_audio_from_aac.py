import av
import simpleaudio as sa
from pydub import AudioSegment
from pydub.playback import play
import time
import wave  
import numpy as np

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




#with open(filename_audio, 'rb') as f:
with wave.open(filename_audio, "rb") as f:
    params = f.getparams()  
    nchannels, sampwidth, framerate, nframes = params[:4]
    print(nchannels, sampwidth, framerate, nframes)
    #f.read(32)
    while f:
        print('play')
        str_data = f.readframes(nframes)
        #b = f.read(2048*2)
        # wave_data = np.frombuffer(str_data, dtype=np.int8)
        # print(wave_data)
        # wave_data.shape = -1,2
        # #转置数据
        # wave_data = wave_data.T
        # print(wave_data)
        #b = f.read(176400)
        #b = f.read(44100)
        play_obj = sa.play_buffer(str_data, 2, 2, 44100)
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

    