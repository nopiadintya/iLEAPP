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

import base64
import struct
from scripts.ilapfuncs import artifact_processor

@artifact_processor
def droneFlightUserInfo(files_found, _report_folder, _seeker, _wrap_text, _timezone_offset):
    """
    Fungsi utama untuk memproses info pengguna drone.
    Argumen yang diawali '_' diabaikan oleh linter (W0613).
    """
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
        if not source_path.lower().endswith(".default"):
            continue
        try:
            with open(source_path, "rb") as file:
                mmv = MMKV(file)
                row = []
                for key in keys_of_interest:
                    raw_val = mmv.get(key)
                    if not raw_val:
                        row.append('')
                        continue
                    try:
                        # Decode base64 value
                        decoded_val = base64.standard_b64decode(raw_val[1:]).decode("utf-8")
                        row.append(decoded_val)
                    except (ValueError, TypeError, base64.binascii.Error) as decode_err:
                        row.append(f"decode_error: {str(decode_err)}")
                data_list.append(tuple(row))
        except (IOError, EOFError):
            continue
        except Exception: # pylint: disable=broad-exception-caught
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
        result = struct.unpack("<I", self.buffer[0:4])[0]
        return result

class MMKV:
    def __init__(self, reader):
        self.reader = MMKVReader(reader)
        self.data = {}
        self.decode()

    def decode(self):
        try:
            self.reader.read_int32_data()
            mmkv_read_raw_varint32(self.reader)
            while True:
                key_bytes = read_key(self.reader)
                if not key_bytes:
                    break
                value = read_value(self.reader)
                key = key_bytes.decode('utf-8')
                if not value:
                    self.data.pop(key, None)
                else:
                    self.data[key] = value
        except (EOFError, IOError, struct.error):
            pass
        except Exception: # pylint: disable=broad-exception-caught
            pass

    def get(self, key):
        return self.data.get(key, b"")

def read_key(reader):
    try:
        count = mmkv_read_raw_varint32(reader)
        if count == 0 or count > 4096:
            return b""
        return reader.read_data(count)
    except (EOFError, IOError):
        return b""

def read_value(reader):
    try:
        count = mmkv_read_raw_varint32(reader)
        if 0 < count < 4096:
            return reader.read_data(count)
        return b""
    except (EOFError, IOError):
        return b""

def mmkv_read_raw_varint32(reader):
    num = 0
    for i in range(5):
        b = reader.read_byte_data()
        num |= (b & 0x7F) << (i * 7)
        if b <= 0x7F:
            return num
    return num
