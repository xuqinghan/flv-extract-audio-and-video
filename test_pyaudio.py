import pyaudio
import wave
import sys

CHUNK = 1024


filename_audio = 'D:/dataset/多瑙河之波.wav'
wf = wave.open(filename_audio, 'rb')

# instantiate PyAudio (1)
p = pyaudio.PyAudio()

# open stream (2)
stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                channels=wf.getnchannels(),
                rate=wf.getframerate(),
                output=True)

# read data
data = wf.readframes(CHUNK)
print(len(data))
# play stream (3)
while len(data) > 0:
    stream.write(data)
    data = wf.readframes(CHUNK)
    print(len(data))

# stop stream (4)
stream.stop_stream()
stream.close()

# close PyAudio (5)
p.terminate()