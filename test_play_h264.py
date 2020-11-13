import av
import cv2
import numpy as np


    
def test_decode_from_file():
    filename_264 = 'out.h264'
    with av.open(filename_264) as container:
        # Signal that we only want to look at keyframes.
        stream = container.streams.video[0]
        #stream.codec_context.skip_frame = 'NONKEY'

        for frame in container.decode(stream):
            #PIL格式
            img = frame.to_image()
            #opencv格式
            img = cv2.cvtColor(np.asarray(img),cv2.COLOR_RGB2BGR)
            print(img)
            cv2.imshow("h264", img)
            k = cv2.waitKey(1)
            if k == 27: # ESC
                break

def test_frame():
    codec = av.CodecContext.create('h264', 'r')



if __name__ == '__main__':
    test_decode_from_file()