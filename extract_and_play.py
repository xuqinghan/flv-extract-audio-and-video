'''
处理stream 而不是一次读取全部数据 

同时出音频，视频帧，并回调而不是直接保存
'''
import struct

AUDIO = 0x8
VIDEO = 0x9
SCRIPT = 0x12

class audio_tag_header:
    '''
    define the audio tag header structure
    '''
    def __init__(self, header_bits):
        self.soundformat = int(header_bits[:4], 2)
        self.soundrate = int(header_bits[4:6], 2)
        self.soundsize = int(header_bits[6], 2)
        self.soundtype = int(header_bits[7], 2)

class video_tag_header:
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


class Parse:

    def __init__(self, flv_stream):
        self.flv_stream = flv_stream
        self._bytes_begin = 13 # 3 + 1 + 1 + 4 + 4
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
        bit_headers = format(0xFFF, 'b') + "0" + "00" + "1" + \
        format(self._audio_object_type-1, "02b") + format(self._sampling_frequency_index, "04b") + \
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
                    self._audio_tag_header = audio_tag_header(format(tag_data[0], 'b'))
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



if __name__ == '__main__':
    fname = './xb2_kos.flv'
    f_stream = open(fname, 'rb')
    #test_read_flvfile_header()
    flvfile_header = parse_flvfile_header(f_stream)
    print(flvfile_header)



    #PreviousTagSize = bytes_to_int(data_bytes)
    #print('PreviousTagSize', PreviousTagSize)

    f_stream.close()