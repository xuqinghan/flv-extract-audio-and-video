'''
处理stream 而不是一次读取全部数据 

同时出音频，视频帧，并回调而不是直接保存
'''

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

class Parse:

    def __init__(self, stream):
        self._flv_data = stream
        self._bytes_begin = 13 # 3 + 1 + 1 + 4 + 4
        self._audio_tag_header = None

    # def header_assert(self):
    #     '''
    #     assert the flv header 
    #     '''
    #     assert(self._flv_data[0] == ord("F"))
    #     assert(self._flv_data[1] == ord("L"))
    #     assert(self._flv_data[2] == ord("V"))
    #     assert(self._flv_data[3] == 1)# assert the flv version

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
        while self._flv_data:

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