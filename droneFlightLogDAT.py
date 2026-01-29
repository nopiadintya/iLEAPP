__artifacts_v2__ = {
    "droneFlightLogDAT": {
        "name": "Drone - .DAT files",
        "description": "Parse log data from DJI Drone DAT files (*.DAT) and Extracts Events.",
        "author": "@NoviAdintya, @HudanStudiawan, @BaskoroAdiPratomo",
        "version": "1.3",
        "date": "2025-03-18",
        "requirements": "DJI drone DAT files (*.DAT)",
        "category": "Drone Logs",
        "notes": "Processes GPS coordinates and timestamps.",
        "paths": ("**/*.DAT",),
        "output_types": "all",
        "artifact_icon": "slack"
    }
} 

from datetime import datetime
import zlib, struct, os
from scripts.ilapfuncs import artifact_processor, logfunc

@artifact_processor
def droneFlightLogDAT(files_found, _report_folder, _seeker, _wrap_text, _timezone_offset):
    """
    Parses DJI Drone DAT files to extract GPS coordinates and timestamps.
    """
    data_list = []
    source_path = ''

    for file_found in files_found:
        source_path = str(file_found)
        if not source_path.lower().endswith(".dat"):
            continue
        try:
            extracted_data = extract_dat(source_path)
            for key, value in extracted_data.items():
                if key.upper().endswith(".DAT") and value[16:21] == b"BUILD":
                    for record in DATFile(value).parse_gps_records():
                        record_time = record[0]
                        longitude = record[1]
                        latitude = record[2]
                        data_list.append((record_time, longitude, latitude))
        except (OSError, zlib.error, struct.error) as e:
            logfunc(f"Error processing {source_path}: {str(e)}")
            continue    
            
    data_headers = (('Timestamp', 'datetime'), "Longitude", "Latitude")
    return data_headers, data_list, source_path
    
def generate_crc_table():
    table = []
    for i in range(256):
        crc = i
        for _ in range(8):
            crc = (crc >> 1) ^ (0x8408 if (crc & 1) else 0)
        table.append(crc)
    return table
crc_table = generate_crc_table()

def check_sum(data):
    v = 13970
    for i in data:
        v = (v >> 8) ^ crc_table[(i ^ v) & 0xFF]
    return v

class DatRecord:
    def __init__(self):
        self.start = 0
        self.len = 0
        self.type = 0
        self.ticket_no = 0
        self.actual_ticket_no = 0
        self.payload = b""
        self.status = "OK"

    def __len__(self):
        return self.len

    def __repr__(self):
        return f"start:{self.start} len:{self.len} type:{self.type} ticket_no:{self.ticket_no} status:{self.status}"

class DATFile:
    def __init__(self, data):
        self.data = data
        self.record_start_pos = 128
        if len(self.data) > 252:
            if self.data[16:21] == b"BUILD":
                if self.data[242:252] == b"DJI_LOG_V3":
                    self.record_start_pos = 256
                else:
                    self.record_start_pos = 128

    def find_next55(self, start):
        try:
            return self.data.index(0x55, start)
        except (ValueError, IndexError):
            return -1

    def parse_records(self):
        record_list = []
        cur_pos = self.record_start_pos
        while cur_pos < len(self.data):
            try:
                if self.data[cur_pos] != 0x55:
                    cur_pos = self.find_next55(cur_pos + 1)
                    if cur_pos == -1: break
                    continue

                if cur_pos + 10 >= len(self.data): break
                
                record_len = self.data[cur_pos+1]
                if record_len < 10 or cur_pos + record_len > len(self.data):
                    cur_pos += 1
                    continue

                crc = check_sum(self.data[cur_pos:cur_pos+record_len-2])
                if crc & 0xFF != self.data[cur_pos+record_len-2] or crc >> 8 != self.data[cur_pos+record_len-1]:
                    cur_pos += 1
                    continue

                record = DatRecord()
                record.start = cur_pos
                record.len = record_len
                record.ticket_no = struct.unpack("<I", self.data[cur_pos+6:cur_pos+10])[0]
                record.type = (self.data[cur_pos+5] << 8) + self.data[cur_pos+4]
                record_list.append(record)
                cur_pos += record_len
            except (struct.error, IndexError):
                cur_pos += 1
        return record_list

    def parse_gps_records(self):
        gps_records = []
        def get_payload(record):
            payload = self.data[record.start+10:record.start+record.len-2]
            return bytes(map(lambda x: x ^ (record.ticket_no % 256), payload))

        for v in [x for x in self.parse_records() if x.type == 2096]:
            try:
                payload = get_payload(v)
                if len(payload) < 16: continue
                date, time, lon, lat = struct.unpack("<IIii", payload[:16])
                year, month, day = int(date/10000), int(date/100)%100, date%100
                hour, minute, second = int(time/10000), int(time/100)%100, time%100
                if year > 2000:
                    gps_records.append([datetime(year, month, day, hour, minute, second), lon/(10**7), lat/(10**7)])
            except (ValueError, struct.error):
                continue
        return gps_records

def extract_dat(path):
    out = {}
    try:
        with open(path, "rb") as f:
            src_data = f.read()
        baseName = os.path.basename(path)
        if not baseName.startswith("DJI_"): 
            out[baseName] = src_data
        else:  
            HEADER_SIZE = 283
            data = zlib.decompress(src_data)
            index = 0
            while index + HEADER_SIZE < len(data):
                try:
                    file_size = struct.unpack("<I", data[index+1:index+5])[0]
                    file_name_raw = data[index+7:index+HEADER_SIZE]
                    index += HEADER_SIZE
                    
                    if b"\x00" in file_name_raw:
                        file_name = file_name_raw[:file_name_raw.index(b"\x00")].decode("utf-8")
                    else:
                        file_name = file_name_raw.decode("utf-8").strip()
                        
                    out[file_name] = data[index:index+file_size]
                    index += file_size
                except (struct.error, ValueError):
                    break
    except (OSError, zlib.error):
        pass
    return out

