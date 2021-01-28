import av

if __name__ == '__main__':
    path_to_video = 'D:/xqh/4dev/zgy/data-origin/inside/多瑙河之波-手风琴.flv'
    fps = 24
    container_in = av.open(path_to_video, mode='r')

    container_out = av.open('test.mp4', mode='w')

    stream_video = container_out.add_stream('h264', rate=fps)
    stream_video.width = 384
    stream_video.height = 288
    stream_video.pix_fmt = 'yuv420p'

    stream_audio = container_out.add_stream('aac', rate=44100)

    for frame in container_in.decode(video=0, audio=0):
        print(frame)

        kind = 'aac' if isinstance(frame, av.AudioFrame) else 'h264'
        if kind == 'h264':
            for packet in stream_video.encode(frame):
                container_out.mux(packet)
        elif kind == 'aac':
            frame.pts = None
            for packet in stream_audio.encode(frame):
                container_out.mux(packet)

    # Flush stream
    for packet in stream_video.encode():
        container_out.mux(packet)

    # Close the file
    container_out.close()