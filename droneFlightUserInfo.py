__artifacts_v2__ = {
    "droneFlightUserInfo": {
        "name": "Drone - .DEFAULT files",
        "description": "Parse log data from DJI Drone User Info files (*.DEFAULT) and Extracts Events.",
        "author": "@NoviAdintya, @HudanStudiawan, @BaskoroAdiPratomo",
        "version": "1.3",
        "date": "2025-03-18",
        "requirements": "DJI drone DEFAULT files (*.DEFAULT)",
        "category": "Drone Logs",
        "notes": "Processes GPS coordinates and timestamps.",
        "paths": ("**/*.DEFAULT"),
        "output_types": "all",
        "artifact_icon": "slack"
    }
} 

import traceback
import zlib,struct,os
from datetime import datetime, timedelta
import io
import base64
from scripts.ilapfuncs import artifact_processor

@artifact_processor
def droneFlightUserInfo(files_found, report_folder, seeker, wrap_text, timezone_offset):
    data_list = []
    source_path = ''

    keys_of_interest = [
        "key_account_nickname", 
        "key_account_id", 
        "key_account_email",
        "key_account_phone", 
        "key_account_uid", 
        "key_account_phone_area"
    ]

    for file_found in files_found:
        source_path = str(file_found)
        if not source_path.endswith(".default"):
            continue
        try:
            with open(source_path, "rb") as file:
                mmv = MMKV(file)
                row = []
                for key in keys_of_interest:
                    raw_val = mmv.get(key)
                    if raw_val is None:
                        row.append('')
                        continue
                    try:
                        decoded_val = base64.standard_b64decode(raw_val[1:]).decode("utf-8")
                        row.append(decoded_val)
                    except Exception as e:
                        row.append(f"decode_error: {str(e)}")
                data_list.append(tuple(row))
        except Exception as e:
            continue
    data_headers = tuple(keys_of_interest)
    return data_headers, data_list, source_path

class MMKVReader:
    def __init__(self, reader):
        self.reader = reader
        self.pos = 0
        self.buffer = bytearray(8)

    def get_pos(self):
        return self.pos

    def read_data(self, size):
        data = self.reader.read(size)
        if len(data) != size:
            if not data:
                raise EOFError("读取错误")
            else:
                raise IOError("读取错误")
        self.pos += len(data)
        return data

    def read_byte_data(self):
        data = self.read_data(1)
        self.buffer[0:1] = data
        return self.buffer[0]

    def read_int32_data(self):
        data = self.read_data(4)
        self.buffer[0:4] = data
        result = (self.buffer[3] << 24) | (self.buffer[2] << 16) | (self.buffer[1] << 8) | self.buffer[0]
        return result

class MMKV:
    def __init__(self, reader):
        self.reader = MMKVReader(reader)
        self.data = {}
        self.decode()

    def decode(self):
        try:
            self.reader.read_int32_data()
            MMKVReadRawVarint32(self.reader)
            while True:
                key = read_key(self.reader)
                value = read_value(self.reader)
                key = key.decode('utf-8')
                # print(key)
                if not value:
                    del self.data[key]
                else:
                    self.data[key] = value     
        except Exception as e:
            # print(f"Error during decoding: {e}")
            pass


    def get(self, key):
        return self.data.get(key, b"")

def read_key(reader):
    count = MMKVReadRawVarint32(reader)
    if count > 4096:
        return b""
    buffer = reader.read_data(count)
    return buffer

def read_value(reader):
    count = MMKVReadRawVarint32(reader)
    if 0 < count < 4096:
        value = reader.read_data(count)
        return value

def MMKVReadRawVarint32(reader):
    num = 0
    for i in range(5):
        b = reader.read_byte_data()
        num |= (b & 0x7F) << (i * 7)
        if b <= 0x7F:
            return num
    for i in range(5):
        if reader.read_byte_data() <= 0x7F:
            break
    return num