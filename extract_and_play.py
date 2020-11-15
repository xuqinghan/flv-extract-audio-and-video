'''
处理stream 而不是一次读取全部数据 

同时出音频，视频帧，并回调而不是直接保存
'''
import struct
from io import BytesIO
#from pydub import AudioSegment
#from bitarray import bitarray
#from flv_decoder import pares_FLVTAGHeader
from enum import Enum
import cv2
import numpy as np
import av
from av.audio.fifo import AudioFifo


import simpleaudio as sa



class TagType(Enum):
    AUDIO = 0x8
    VIDEO = 0x9
    SCRIPT = 0x12

class CodecIDVideo(Enum):
    AVC = 7

class AVCPacketType(Enum):
    header = 0
    NALU = 1
    end = 2

class H264FrameType(Enum):
    key = 1
    inter = 2



class TagHeaderAudio:
    '''
    define the audio tag header structure
    '''
    def __init__(self, header_bits):
        self.soundformat = int(header_bits[:4], 2)
        self.soundrate = int(header_bits[4:6], 2)
        self.soundsize = int(header_bits[6], 2)
        self.soundtype = int(header_bits[7], 2)
    
    def __str__(self):
        return f'soundformat: {self.soundformat}, soundrate: {self.soundrate}, soundsize:{self.soundsize}, soundtype:{self.soundtype}'

class TagHeaderVideo:
    '''
    defiune the video tag header structure
    '''
    def __init__(self, header_data):
        self.sps = header_data[10] & 0x1f
        self.sps_data_length = bytes_to_int(header_data[11:13])
        self.sps_data = header_data[13:13+self.sps_data_length]
        self.pps = header_data[13+self.sps_data_length] & 0x1f
        self.pps_data_length = bytes_to_int(header_data[14+self.sps_data_length:16+self.sps_data_length])
        self.pps_data = header_data[16+self.sps_data_length:16+self.sps_data_length+self.pps_data_length]

def bytes_to_int(bytes_string):
    '''
    pack of the int.from_bytes
    '''
    return int.from_bytes(bytes_string, byteorder="big")

def parse_flvfile_header(f_stream):
    '''
        FLV格式参考 https://blog.csdn.net/byxdaz/article/details/53993791
            # 
        struct unpack 用 'B' 转成 8bit的 short 然后才可以用 & 和 >> 得到值了
        用bytes  反而难操作
        已经写到了cnblog：https://www.cnblogs.com/xuanmanstein/p/13967320.html
    '''
    ##header 9 字节
    chunk = f_stream.read(9)
    # s 仍然是1个Bytes 不好处理，读成1个short然后才能位操作
    #format_str = '>3sBsI'
    format_str = '>3sBBI'
    flv, version, stream_type_bits, len_header = struct.unpack(format_str, chunk)

    has_audio =  (stream_type_bits & 0x7) >> 2
    has_video = stream_type_bits &  0x1

    return {'version': version,
            'has_video': has_video,
            'has_audio': has_audio, 
            'len_header': len_header} #len_header 9 字节

def parseTAGheader(data_bytes):
    '''TAG header 11字节'''

    #print(data_bytes[0])
    tag_type = TagType(data_bytes[0])
    #print(tag_type)
    #24bit
    size_DATA = bytes_to_int(data_bytes[1:4])
    #print('size_DATA', size_DATA)
    timestamp = bytes_to_int(data_bytes[4:8])
    #print('timestamp', timestamp)
    StreamID = bytes_to_int(data_bytes[8:])
    return {'TagType': tag_type,
     'DataSize': size_DATA, 
     'timestamp':timestamp, 
     'StreamID':StreamID}
     
def parse_avc_from_tag_video(data_tag_bytes):
    #4bit
    FrameType_CodecID = data_tag_bytes[0]
    CodecID = CodecIDVideo(data_tag_bytes[0] & 0x0F)
    FrameType = data_tag_bytes[0] >> 4
    #print(f'CodecID, {CodecID} FrameType {FrameType}')
    if CodecIDVideo.AVC != CodecID:
        return None

    #只处理AVC
    type_AVCPacket = AVCPacketType(data_tag_bytes[1])
    CompoistionTime = data_tag_bytes[3]


    #begin_DATA = 5
    return  {'AVCPacketType': type_AVCPacket, 
            'keyframe': H264FrameType(FrameType), 
            'CompoistionTime' : CompoistionTime,
            'data':  data_tag_bytes[5:]} #包括NALU数据长度
 
def parse_NALUs_from_avc_data(data_avc):
    '''用于字节流形式的NALU  多个NALU
        不加 b"\x00\x00\x00\x01"
    '''
    NALUs = []
    begin = 0
    size_bytes = len(data_avc)
    while begin < size_bytes:
        #4byte NALU长度
        nalu_length = bytes_to_int(data_avc[begin:begin+4])
        begin += 4
        #NALU内容
        NALUs.append(data_avc[begin:begin+nalu_length])
        begin += nalu_length

    assert begin==size_bytes
    return NALUs

# def parse_FLV_TAG1(f_tag):
#     PreviousTagSize, *_ = struct.unpack('>I', f_tag.read(4))
#     #print('PreviousTagSize0', PreviousTagSize)
#     #print('----------------flv_tag begin----------------')
#     #总是0
#     header = pares_FLVTAGHeader(BytesIO(f_tag.read(11)))
#     #print(header)
#     #XXXTag
#     DATA = f_tag.read(header['DataSize'])
#     #print('DATA', DATA)
#     #print('-----DATA-----------')
#     f_data = BytesIO(DATA)
#     if header['TagType'] == 'video':
#         body = parse_DATA_of_VIDEOTAG(f_data)
#     elif header['TagType'] == 'audio':
#         #print('DATA', DATA.hex())
#         body = parse_DATA_of_AUDIOTAG(f_data)
#     else:
#         raise Exception(f"unknown TagType {header['TagType']}")
#     #res = f_tag.read()
#     #assert len(res) == 0
#     #print('----------------flv_tag end----------------')
#     return {'header': header, 'body': body}

def calculate_sampling_frequency_index(data_tag):
    '''
    '''
    bytes_string = data_tag[2:]
    left = bytes_string[0]
    right = bytes_string[1]
    sampling_frequency_index = ((left & 0x7) << 1) | (right >> 7)
    return sampling_frequency_index

def calculate_audio_object_type(data_tag):
    bytes_string = data_tag[2:]
    left = bytes_string[0]
    audio_object_type = (left & 0xF8) >> 3
    return  audio_object_type

def make_adts_headers(data_size, audio_object_type, sampling_frequency_index):
    '''
    according to the doc, add adts headers
    for flv size_data = size_tag - 2!
    '''
    # adts_fixed_header
    #ID 0 MPEG-4  Layer：always: '00'  profile "1" protection_absent LC
    bit_headers = format(0xFFF, 'b') + "0" + "00" + "1" + \
    format(audio_object_type-1, "02b") + format(sampling_frequency_index+1, "04b") + \
    "0" + format(2, "03b") + "0" + "0"

    #adts_variable_header
    bit_headers += "0" + "0" + format(7+data_size, "013b") + format(0x7FF, "011b") + "00"
    int_list = [int(bit_headers[8*x:8*x+8], 2) for x in range(7)]
    return bytes(int_list)




class Parse:

    def __init__(self, flv_stream):
        self.flv_stream = flv_stream
        #self._bytes_begin = 13 # 3 + 1 + 1 + 4 + 4
        self._audio_tag_header = None


    def calculate_audio_specific_config(self, bytes_string):
        '''
        calculate sampling frequency index value
        '''
        left = bytes_string[0]
        right = bytes_string[1]
        self._sampling_frequency_index = ((left & 0x7) << 1) | (right >> 7)
        self._audio_object_type = (left & 0xF8) >> 3


    def make_adts_headers(self, tag_data_size):
        '''
        according to the doc, add adts headers
        '''
        # adts_fixed_header
        # ID 0 MPPEG-4  layer always '00'
        bit_headers = format(0xFFF, 'b') + "0" + "00" + "1" + \
        format(self._audio_object_type-1, "02b") + format(self._sampling_frequency_index+1, "04b") + \
        "0" + format(2, "03b") + "0" + "0"
        #adts_variable_header
        bit_headers += "0" + "0" + format(7+tag_data_size, "013b") + format(0x7FF, "011b") + "00"
        int_list = [int(bit_headers[8*x:8*x+8], 2) for x in range(7)]
        return bytes(int_list)

    def extract(self):
        '''
        seperate the audio from the vedio.
        '''
        #current = self._bytes_begin
        while self.flv_stream:
            
            tag_type = self._flv_data[current]         
            tag_data_size = bytes_to_int(self._flv_data[current+1:current+4])
            tag_data = self._flv_data[current+11:current+11+tag_data_size]
            if tag_type == AUDIO:
                if self._audio_tag_header is None:
                    self._audio_tag_header = TagHeaderAudio(format(tag_data[0], 'b'))
                    assert(self._audio_tag_header.soundformat == 10)
                    assert(tag_data[1] == 0x00)
                    self.calculate_audio_specific_config(tag_data[2:])
                else:
                    self._acc_data += self.make_adts_headers(tag_data_size-2) + tag_data[2:]
            current += 11 + tag_data_size
            assert(bytes_to_int(self._flv_data[current:current+4]) == 11 + tag_data_size)
            current += 4

def test_read_flvfile_header_without_struct():
    '''不用struct'''
    fname = './xb2_kos.flv'
    f_stream = open(fname, 'rb')

    data_bytes = f_stream.read(9)
    flv = data_bytes[0:3]

    print(flv)
    version = data_bytes[3]
    print('version', version)
    print(len(data_bytes))
    #从bytes里取出来了就是是int！
    print(type(data_bytes[4]))
    #转为str 'b' 补足8位
    stream_type_bits = format(data_bytes[4], 'b').zfill(8)
    print('stream_type_bits', stream_type_bits, type(stream_type_bits))
    #按bit取出string，按二进制再转成int
    has_audio = int(stream_type_bits[5], 2)
    print('has_audio', has_audio)
    has_video = int(stream_type_bits[7], 2)
    print('has_video', has_video)
    len_header = bytes_to_int(data_bytes[5:])
    print('len_header', len_header)


def test_parse(f_stream, fn_frame_acc, fn_frame_h264):
    codec_audio = av.CodecContext.create('aac', 'r')
    codec_video = av.CodecContext.create('h264', 'r')
    #------------flv header-----------------
    #test_read_flvfile_header()
    flvfile_header = parse_flvfile_header(f_stream)
    #print(flvfile_header)

    #--------------flv body-------------------
    audio_tag_header = None
    video_tag_header = None
    first_video = True
    i = 0
    while i < 1500:
        i += 1
        #print(i)
        data_bytes = f_stream.read(4)
        PreviousTagSize = bytes_to_int(data_bytes)
        #print('PreviousTagSize', PreviousTagSize)
        #------------HEAD-------------
        #print('----------------flv_tag begin----------------')
        data_bytes = f_stream.read(11)
        header = parseTAGheader(data_bytes)
        #header = pares_FLVTAGHeader(f_stream)
        #print(header)
        #print(header['TagType'] ==TagType.SCRIPT)
        #-------------DATA--------------------
        size_data_tag = header['DataSize']
        data_tag = f_stream.read(size_data_tag)
        tag_type = header['TagType']
        if tag_type == TagType.AUDIO:
            #print(audio_tag_header)
            if audio_tag_header is None:
                #说明是第一帧，丢弃 只有size 4
                audio_tag_header = TagHeaderAudio(format(data_tag[0], 'b'))
                #print(audio_tag_header)
                sampling_frequency_index = calculate_sampling_frequency_index(data_tag)
                audio_object_type = calculate_audio_object_type(data_tag)
                #print('sampling_frequency_index', sampling_frequency_index)
                #print('audio_object_type', audio_object_type)
                continue
            else:
                adts_headers = make_adts_headers(size_data_tag-2, audio_object_type, sampling_frequency_index)
                #print('adts_headers', adts_headers)
                #重组aac一帧 加入了adts
                #print('size', size_data_tag)
                frame_acc = adts_headers + data_tag[2:]
                #print(adts_headers, data_tag[2:])
                #写入
                fn_frame_acc(frame_acc, codec_audio)
        elif tag_type == TagType.VIDEO:
            avc1 = parse_avc_from_tag_video(data_tag)
            if avc1 is None:
                continue

            #print(f'size_data_tag {size_data_tag} ', avc1)
            if avc1['AVCPacketType'] == AVCPacketType.header:
                video_tag_header = TagHeaderVideo(data_tag)
                data_write = b"\x00\x00\x00\x01" + video_tag_header.sps_data + b"\x00\x00\x00\x01" + video_tag_header.pps_data
                #print('avc header')
                #header 的 avc1['data'] 就是 extradata
                #写这个导致异常退出！
                #codec_video.extradata = avc1['data']
                # #写header的数据 
                # with open('./dumps/avc_header_for_saveh264.dump', 'wb') as f:
                #     extradata = f.write(data_write)

                fn_frame_h264(data_write, None)
            elif avc1['AVCPacketType'] == AVCPacketType.NALU:
                NALUs = parse_NALUs_from_avc_data(avc1['data'])
                #print(f'{i}NALUs', len(NALUs), NALUs)
                #if i == 4:
                if first_video:
                    #print('first idx=', i)
                    #第一个NALU里有 BiliBili H264 Encoder v1.0 舍弃
                    NALUs = NALUs[1:]
                    first_video = False

                for nalu in NALUs:
                    data_write = b"\x00\x00\x00\x01" + nalu
                    fn_frame_h264(data_write, codec_video)

        else:
            #只处理音频和视频 其他帧放弃
            continue

    return 


    


if __name__ == '__main__':


    #通过codec_name = container.streams[video_stream_index].codec_context
    # with open('./dumps/h264_extradata.dump', 'rb') as f:
    #     extradata = f.read()
    #codec_video.extradata = extradata

    sample_rate = 24000
    sec_play = 10
    samples_play_once = sample_rate*sec_play

    audio_fifo = AudioFifo()

    fname_out_acc = './dumps/out.aac'
    f_out_acc = open(fname_out_acc, 'wb')

    def fn_frame_acc(bytes_frame, codec_audio):
        #f_out_acc.write(bytes_frame)
        pass
        #解码
        #packets = codec_audio.parse(frame_acc)
        #not parse #https://github.com/PyAV-Org/PyAV/issues/155
        packet = av.packet.Packet(bytes_frame)
        frames = codec_audio.decode(packet)
        print('audio frames', frames)
        for frame in frames:
            audio_fifo.write(frame)
            # decoded_data = frame.planes[0].to_bytes()
            # play_obj = sa.play_buffer(decoded_data, 2, 2, 44100)
            # play_obj.wait_done()



    fname_out_h264 = './dumps/out.h264'
    f_out_h264 = open(fname_out_h264, 'wb')

    def fn_frame_h264(bytes_frame, codec_video):
        #f_out_h264.write(bytes_frame)
        pass
        # if codec_video is None:
        #     #header 不需要解码
        #     return
        # #解码
        # packet = av.packet.Packet(bytes_frame)
        # #print(packet)
        # frames_img = codec_video.decode(packet)
        # #print(frames)
        # for frame_img in frames_img:
        #     #PIL
        #     img = frame_img.to_image()
        #     #opencv
        #     img = cv2.cvtColor(np.asarray(img),cv2.COLOR_RGB2BGR)
        #     cv2.imshow("h264", img)
        #     k = cv2.waitKey(1)
        #     if k == 27: # ESC
        #         break


    fname = './xb2_kos.flv'
    f_stream = open(fname, 'rb')

    print('begin')
    test_parse(f_stream, fn_frame_acc, fn_frame_h264)
    #play
    print('play audio')
    frames = audio_fifo.read_many(samples=samples_play_once)
    print(frames)
    for frame in frames:
        data_wait_play = frame.planes[0].to_bytes()
        play_obj = sa.play_buffer(data_wait_play, 2, 4, sample_rate)
        play_obj.wait_done()
    # while True:
    #     if audio_fifo.samples >= samples_play_once:
    #         print('player: get data from queue')
    #         frame = audio_fifo.read(samples_play_once)
    #         data_wait_play = frame.planes[0].to_bytes()
    #         print('player: start play', datetime.now())
    #         play_obj = sa.play_buffer(data_wait_play, 2, 4, sample_rate)
    #         play_obj.wait_done()



    #parse = Parse(f_stream)


    
    #18 0x12 脚本


    #如果32位读取，移位
 
    f_stream.close()
    f_out_acc.close()
    f_out_h264.close()