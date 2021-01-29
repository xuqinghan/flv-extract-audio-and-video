import av

class RecordVideo(object):
    """一段录像"""
    def __init__(self, name, pts_save_t0, width, height):
        super(RecordVideo, self).__init__()
        self.container = av.open(f'{name}.mp4', mode='w')
        self.stream_video = self.container.add_stream('h264', rate=24)
        self.stream_video.width = width
        self.stream_video.height = height
        self.stream_video.pix_fmt = 'yuv420p'
        self.stream_audio = self.container.add_stream('aac', rate=44100)
        self.pts_save_t0 = pts_save_t0

    def save_frame1_audio(self, frame):
        # if self.pts_save_t0 is not None:
        #     frame.pts = frame.pts - self.pts_save_t0
        #和视频不同 设置为NOne不影响播放
        frame.pts = None
        print(f'实际保存 音频帧 {frame} time = {frame.time} pts={frame.pts} time_base={frame.time_base}')


        for packet in self.stream_audio.encode(frame):
            self.container.mux(packet)

    def save_frame1_video(self, frame):
        if self.pts_save_t0 is not None:
            frame.pts = frame.pts - self.pts_save_t0

        print(f'实际保存 视频帧 {frame} time = {frame.time} pts={frame.pts} time_base={frame.time_base}')

        for packet in self.stream_video.encode(frame):
            self.container.mux(packet)

    def end(self):
        # Close the file
        self.container.close()


class Recorder(object):
    '''录像机 on_frame作为 rx的订阅者'''
    def __init__(self, fn_reocrd_name1, event_need_record):
        self.fn_reocrd_name1 = fn_reocrd_name1
        self.event_need_record = event_need_record
        self.record1_video = None #当前录像段


    def on_frame(self, kind, frame):
        '''收到1帧，但是可以不处理，只在event_need_record时才处理'''
        if self.event_need_record.is_set():
            #玩家通知开始录像
            #kind, frame = args
            #kind = 'aac' if isinstance(frame, av.AudioFrame) else 'h264'

            if self.record1_video is None:
                #没开始 需要视频帧进行初始化
                if kind == 'h264':
                    print('录像机开始1个新录像')
                    #f'{datetime.now().isoformat()}'
                    fname = self.fn_reocrd_name1()
                    self.record1_video = RecordVideo(fname, frame.pts, frame.width, frame.height)
                else:
                    #不是视频帧。没初始化好，不继续
                    return

            if kind == 'h264':
                print('保存图像',frame)
                self.record1_video.save_frame1_video(frame)
            elif kind == 'aac':
                print('保存音频',frame)
                self.record1_video.save_frame1_audio(frame)

        else:
            #玩家通知停止录像
            if self.record1_video is not None:
                print('正在录像 停止')
                self.record1_video.end()
                self.record1_video = None
            else:
                #本来停止中，玩家通知停止，无动作
                pass