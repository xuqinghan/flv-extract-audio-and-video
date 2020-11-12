from io import BytesIO
from bitarray import bitarray
import struct
from datetime import datetime
# from cv2 import cv2
# import av
#import ffmpeg
# import librtmp

import pickle
import time

def r24(f):
	a, b, c = f.read(3)
	return a << 16 | b << 8 | c


def parse_flvfile_header(stream):
    #FLV格式参考 https://blog.csdn.net/byxdaz/article/details/53993791
    #header 3byte
    #print(line, len(line))
    chunk = stream.read(9)
    flv, version, stream_type_bytes, len_header = struct.unpack('>3sBsI', chunk)

    stream_type = bitarray(endian='big')
    stream_type.frombytes(stream_type_bytes)
    has_video, has_audio = stream_type[-1], stream_type[-3]
    print(f'version= {version}\
            has_video {has_video}, \
            has_audio {has_audio}, \
            len_header {len_header}')
    #header 9 字节结束
    return {'version': version,
            'has_video': has_video,
            'has_audio': has_audio, 
            'len_header': len_header}

#FLV
TagTypes = {8: 'audio', 9: 'video', 18: 'script'}
Filters = {0: 'unencrypted', 1: 'encrypted'}
#DATA VIDEO
Video_FrameTypes = {1: "key", 2: 'inter', 3: 'disposable inter',4:'generated key',5: 'video info'}
Video_CodecIDs = {2: 'Sorenson H.263', 3:'Screen video', 4: 'On2 VP6', 5: 'On2 VP6 with alpha', 7: 'AVC'}
Video_AVCPacketTypes = {0: 'header', 1: 'NALU', 2: 'end'}
#DATA AUDIO
AudioTypes = {0: 'Linear PCM, big endian', 
1: 'ADPCM',
2: 'MP3',
3: 'Linear PCM, little endian',
4: 'Nellymoser 16kHz mono',
5: 'Nellymoser 8kHz mono',
6: 'Nellymoser',
7: 'G.711 A-law logarithmic PCM',
8: 'G.711 mu-law logarithmic PCM',
9: 'reserved',
10: 'AAC',
11: 'Speex',
14: 'MP3 8kHz',
15: 'Device-specific sound'
}


def pares_FLVTAGHeader(f_pkg):
    '''FLVTAG 11字节'''
    #tag1
    #Tag_kind, *_ = struct.unpack('>B', f_pkg.read(1))


    R_Filter_TagType = bitarray(endian='big')
    R_Filter_TagType.frombytes(f_pkg.read(1))
    #
    Reserved = R_Filter_TagType[0:2]
    #print('Reserved', Reserved)
    Filter = Filters.get(R_Filter_TagType[2])
    #print(Filter)
    ba = 3* bitarray([False]) + R_Filter_TagType[3:8]
    #print(ba, len(ba))
    TagType, *_ = struct.unpack('>B', ba.tobytes())
    TagType = TagTypes.get(TagType)
    #print(TagType)
    #Message 长度
    DataSize = r24(f_pkg)
    #30
    #print('DataSize', DataSize)
    timestamp, *_ = struct.unpack('>I', f_pkg.read(4))
    #第一个tag总是0
    #print('timestamp', timestamp)
    StreamID = r24(f_pkg)
    #print('StreamID', StreamID)

    return {'TagType': TagType, 'DataSize': DataSize, 'timestamp':timestamp, 'StreamID':StreamID}

def parse_AVCDecoderConfigurationRecord(f_data):
    '''AVC sequence header的后续
        参考 https://www.jianshu.com/p/0c882eca979c
    '''
    version, *_ = struct.unpack('>B', f_data.read(1))
    #print('version', version)
    sps = [f_data.read(1) for i in range(3)]
    #print('sps', sps)
    lengthSizeMinusOne = bitarray(endian='big')
    lengthSizeMinusOne.frombytes(f_data.read(1))
    ba = 6 * bitarray([False]) + lengthSizeMinusOne[6:8]
    lengthSizeMinusOne, *_ = struct.unpack('>B', ba.tobytes())
    #3
    #print('lengthSizeMinusOne', lengthSizeMinusOne)
    numSPS = bitarray(endian='big')
    numSPS.frombytes(f_data.read(1))
    ba = 3 * bitarray([False]) + numSPS[3:8]
    numSPS, *_ = struct.unpack('>B', ba.tobytes())
    # 1
    #print('numSPS', numSPS)
    SPS_Length, *_ = struct.unpack('>H', f_data.read(2)) 
    #print('SPS_Length', SPS_Length)
    #sps内容 注意和上面的区别
    SPSNALUnits = f_data.read(SPS_Length)
    #1
    numPPS, *_ = struct.unpack('>B', f_data.read(1))
    #print('numPPS', numPPS)
    PPS_Length, *_ = struct.unpack('>H', f_data.read(2)) 
    #print('PPS_Length', PPS_Length)
    #pps内容
    PPSNALUnits = f_data.read(PPS_Length)

    #'numSPS':numSPS, 
    return {'sps': sps, 
    'lengthSizeMinusOne':lengthSizeMinusOne, 
    'SPSNALUnits':SPSNALUnits,
    'PPSNALUnits':PPSNALUnits,
    }

def parse_VIDEO_NALU(f_data):
    '''
    #开头 8bit 未知  不稳定  00002644
    000025fc
    # 67 SPS？ #742001495a8582590 稳定
    67 42 00 14  95 a8 58 25 90 00000001
    # 68 PPS #稳定
    68ce3c80 00000001   
    ## Slice ? 略有变化 06e501fb80
    06 e5 01 07 80 00000001  
    #NALU header  065 IDR帧  总共9700-9800 再无 0000 0001 分割符？
    65b8000009c1d025f1088e10fc3d0045361908d5a86088c29e23611f62b7581acb8123c1dd7b67b62dc9fed0cfa751f83fa765b265d168a3f00efeab5aa2f45fc278
    '''
    b = f_data.read()
    #print(b.hex())
    return b

def parse_DATA_of_VIDEOTAG(f_data):
    '''视频的DATA部分'''
    FrameType_CodecID = bitarray(endian='big')
    FrameType_CodecID.frombytes(f_data.read(1))
    ba = 4* bitarray([False]) + FrameType_CodecID[0:4]
    FrameType, *_ = struct.unpack('>B', ba.tobytes())
    FrameType = Video_FrameTypes.get(FrameType)
    #print('FrameType', FrameType)
    ba = 4* bitarray([False]) + FrameType_CodecID[4:8]
    CodecID, *_ = struct.unpack('>B', ba.tobytes())
    CodecID = Video_CodecIDs.get(CodecID)
    #print('CodecID', CodecID)
    if CodecID == 'AVC':
        AVCPacketType, *_ = struct.unpack('>B', f_data.read(1))
        AVCPacketType = Video_AVCPacketTypes.get(AVCPacketType)
        #print('AVCPacketType', AVCPacketType)
        #print(len(f_data.read(3)))
        #3字节0 #看图https://www.jianshu.com/p/0c882eca979c
        CompositionTime = r24(f_data)
        #print('CompositionTime', CompositionTime)
        if AVCPacketType == 'header':
            #AVCDecoderConfigurationRecord
            body = parse_AVCDecoderConfigurationRecord(f_data)
        elif AVCPacketType == 'NALU':
            #NALU
            body = parse_VIDEO_NALU(f_data)
        #TagType, *_ = struct.unpack('>B', f_data.read(1))
        #res = f_data.read()
        #应该恰好为0
        #assert len(res) == 0
        #print('DATA剩余', len(res), res)
    return {'FrameType': FrameType, 
            #'CodecID' : CodecID,
            'AVCPacketType': AVCPacketType, 
            'data': body}


def parse_DATA_of_AUDIOTAG(f_data):
    '''音频的DATA部分'''
    AudioType_SAMPLERATE_L_TYPE = bitarray(endian='big')
    AudioType_SAMPLERATE_L_TYPE.frombytes(f_data.read(1))
    ba = 4* bitarray([False]) + AudioType_SAMPLERATE_L_TYPE[0:4]
    AudioType, *_ = struct.unpack('>B', ba.tobytes())
    AudioType = AudioTypes.get(AudioType)
    #print('AudioType', AudioType)
    ba = 6* bitarray([False]) + AudioType_SAMPLERATE_L_TYPE[4:6]
    SampleRate, *_ = struct.unpack('>B', ba.tobytes())
    # AAC
    assert SampleRate == 3
    #print('SampleRate', SampleRate)
    #print(AudioType_SAMPLERATE_L_TYPE)
    ba = 7* bitarray([False]) + bitarray([AudioType_SAMPLERATE_L_TYPE[6]])
    SampleLen, *_ = struct.unpack('>B', ba.tobytes())
    # AAC 16bit
    assert SampleLen == 1
    #print('SampleLen', SampleLen)
    ba = 7* bitarray([False]) + bitarray([AudioType_SAMPLERATE_L_TYPE[7]])
    TYPE, *_ = struct.unpack('>B', ba.tobytes())
    # AAC 16bit
    assert TYPE == 1
    DATA_AUDIO = f_data.read()
    #print('DATA_AUDIO', DATA_AUDIO.hex())
    return {'AudioType': AudioType, 'data': DATA_AUDIO}

def parse_FLV_TAG1(f_tag):
    PreviousTagSize, *_ = struct.unpack('>I', f_tag.read(4))
    #print('PreviousTagSize0', PreviousTagSize)
    #print('----------------flv_tag begin----------------')
    #总是0
    header = pares_FLVTAGHeader(BytesIO(f_tag.read(11)))
    #print(header)
    #XXXTag
    DATA = f_tag.read(header['DataSize'])
    #print('DATA', DATA)
    #print('-----DATA-----------')
    f_data = BytesIO(DATA)
    if header['TagType'] == 'video':
        body = parse_DATA_of_VIDEOTAG(f_data)
    elif header['TagType'] == 'audio':
        #print('DATA', DATA.hex())
        body = parse_DATA_of_AUDIOTAG(f_data)
    else:
        raise Exception(f"unknown TagType {header['TagType']}")
    #res = f_tag.read()
    #assert len(res) == 0
    #print('----------------flv_tag end----------------')
    return {'header': header, 'body': body}


def parse_first_tag(chuck):
    '''第一个tag，在wireshark里是244后的第一个99'''
    f_tag = BytesIO(chuck)
    return parse_FLV_TAG1(f_tag)
    #print('第一包剩余', len(res), res)    
    #PreviousTagSize, *_ = struct.unpack('>I', f_pkg.read(4))
    #总是0
    #print('PreviousTagSize1', PreviousTagSize)

def parse_tags(stream, fname_pkg:str):
    '''根据wireshark 前5包长度是确定的！

    '''
    # 前9个是头
    #num_byte = 9
    #pkg2 = stream.read(num_byte)
    #从FLV开始，464c56c90500000009
    #对应wireshark第2个244的“返回HTTP 200”包的末尾附件部分 Content-Type: Flash ...FLV..
    #print('pkg2', pkg2.hex())
    parsed_frames = []
    flv_header = parse_flvfile_header(stream)
    #wireshark第3包
    num_byte = 45
    pkg3 = stream.read(num_byte)
    #print('pkg3', pkg3.hex())
    frame1 = parse_first_tag(pkg3)
    parsed_frames.append(frame1)
    #every FLV_tag
    time.sleep(0.01)
    i = 2
    while True:
        print(f'第{i}FLVTAG')
        if i >500: #500段FLV帧，音视频混
            break
        frame1 = parse_FLV_TAG1(stream)
        parsed_frames.append(frame1)
        time.sleep(0.01)
        i += 1

    with open(fname_pkg, 'wb') as f:
        pickle.dump(parsed_frames, f)
    #pkg4 = stream.read(1412) 
    #print('pkg4', pkg4.hex())

    # pkg3 = stream.read(99)
    # pkg4 = stream.read(1466)
    # pkg5 = stream.read(1090)
    # "\xd4\x6d\x6d\x61\xae\xbd\xc0\x56\x27\xbb\x61\x7f\x08\x00\x45\x00" \
    # "\x00\x34\x4e\xbc\x40\x00\x30\x06\xf4\x1a\x78\x19\xcd\xa7\xc0\xa8" \
    # "\x01\x84\x19\xcc\xe8\xdb\xda\x8a\x2d\xda\x8a\x5a\xa2\xa0\x80\x12" \
    # "\x20\x00\x0f\x3b\x00\x00\x02\x04\x05\x84\x01\x03\x03\x08\x01\x01" \
    # "\x04\x02"

