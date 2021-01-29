'''
    异步版本从文件流解析1个flv  stream-> pyav 
    发送保存pyav frame
    单文件stream解码， 用于改造为rmtp解码参考！
'''
import struct
from io import BytesIO

from enum import Enum



import asyncio

import av
import copy


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
    format(audio_object_type-1, "02b") + format(sampling_frequency_index, "04b") + \
    "0" + format(2, "03b") + "0" + "0"

    #adts_variable_header
    bit_headers += "0" + "0" + format(7+data_size, "013b") + format(0x7FF, "011b") + "00"
    int_list = [int(bit_headers[8*x:8*x+8], 2) for x in range(7)]
    return bytes(int_list)


codec_aac = av.CodecContext.create('aac', 'r')
codec_h264 = av.CodecContext.create('h264', 'r')

def get_frames_pyav(chunk, codec):
    '''利用pyAV'''
    packets = codec.parse(chunk)
    #print(packets)
    frames = []
    for packet in packets: 
        frames = codec.decode(packet)

    return frames

async def parse_stream1(f_stream, event_live_end, sender, time_base, time_stamp_f):

    #------------flv header-----------------
    #test_read_flvfile_header()
    flvfile_header = parse_flvfile_header(f_stream)
    #print(flvfile_header)

    #--------------flv body-------------------
    audio_tag_header = None
    video_tag_header = None
    data_write_header = None #每帧头部添加sps pps
    first_video = True
    i = 0

    while f_stream:

        if event_live_end.is_set():
            #停止直播，退出
            break


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
        timestamp = header['timestamp']
        print('timestamp', timestamp)
        kind = None
        frames = []

        pts = timestamp/time_stamp_f

        if tag_type == TagType.AUDIO:
            kind = 'aac'
            #print(audio_tag_header)
            if audio_tag_header is None:
                #说明是第一帧，丢弃 只有size 4
                audio_tag_header = TagHeaderAudio(format(data_tag[0], 'b'))
                #print(audio_tag_header)
                sampling_frequency_index = calculate_sampling_frequency_index(data_tag)
                audio_object_type = calculate_audio_object_type(data_tag)
                print('sampling_frequency_index', sampling_frequency_index)
                print('audio_object_type', audio_object_type)
                continue
            else:
                adts_headers = make_adts_headers(size_data_tag-2, audio_object_type, sampling_frequency_index)
                #print('adts_headers', adts_headers)
                #重组aac一帧 加入了adts
                #print('size', size_data_tag)
                chunk = adts_headers + data_tag[2:]
                #print(adts_headers, data_tag[2:])
                #写入
                #fn_frame_acc(frame_acc, codec_audio)
                #解码？
                frames.extend(get_frames_pyav(chunk, codec_aac))

        elif tag_type == TagType.VIDEO:
            kind = 'h264'
            avc1 = parse_avc_from_tag_video(data_tag)
            if avc1 is None:
                continue

            #print(f'size_data_tag {size_data_tag} ', avc1)
            if avc1['AVCPacketType'] == AVCPacketType.header:
                video_tag_header = TagHeaderVideo(data_tag)

                data_write_header = b"\x00\x00\x00\x01" + video_tag_header.sps_data + b"\x00\x00\x00\x01" + video_tag_header.pps_data
                #print('avc header')
                #header 的 avc1['data'] 就是 extradata
                #写这个导致异常退出！ 
                #codec_video.extradata = avc1['data']
                # #写header的数据 
                # with open('./dumps/avc_header_for_saveh264.dump', 'wb') as f:
                #     extradata = f.write(data_write)

                #fn_frame_h264(data_write, None)

            elif avc1['AVCPacketType'] == AVCPacketType.NALU:
                #头部信息，在flv文件里只有1次，在rtmp里, 每帧都有
                chunk = copy.deepcopy(data_write_header)
                nalu_length = bytes_to_int(data_tag[5:9])
                begin = 9
                if begin + nalu_length == size_data_tag:
                    chunk += b"\x00\x00\x00\x01" + data_tag[9:]
                else:
                    while True:
                        chunk += b"\x00\x00\x00\x01" + data_tag[begin:begin+nalu_length]
                        begin += nalu_length
                        if begin == size_data_tag:
                            break
                        nalu_length = bytes_to_int(data_tag[begin:begin+4])
                        begin += 4
                #解码？
                CompoistionTime = avc1['CompoistionTime']
                #pts = timestamp + CompoistionTime
                print(f'timestamp {timestamp} CompoistionTime={CompoistionTime}')
                frames.extend(get_frames_pyav(chunk, codec_h264))


        else:
            #只处理音频和视频 其他帧放弃
            continue

        print('直播中')
        #加pts
        print('pts', pts)
        for frame in frames:
            frame.pts=pts
            frame.time_base = time_base

    
        print('解码结果', kind, frames)
        if frames:
            #有结果
            print('发送走')
            [sender(kind, frame1) for frame1 in frames]

        await asyncio.sleep(0.01)
