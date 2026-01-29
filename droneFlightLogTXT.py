__artifacts_v2__ = {
    "droneFlightLogTXT": {
        "name": "Drone - .TXT files",
        "description": "Parse log data from DJI Drone TXT files (*.TXT) and Extracts Events.",
        "author": "@NoviAdintya, @HudanStudiawan, @BaskoroAdiPratomo",
        "version": "1.3",
        "date": "2025-03-18",
        "requirements": "DJI drone TXT files (*.TXT)",
        "category": "Drone Logs",
        "notes": "Processes GPS coordinates and timestamps.",
        "paths": ("**/*.TXT"),
        "output_types": "all",
        "artifact_icon": "slack"
    }
}

import math
import struct
from datetime import datetime
from enum import Enum
from scripts.ilapfuncs import artifact_processor

@artifact_processor
def droneFlightLogTXT(files_found, _report_folder, _seeker, _wrap_text, _timezone_offset):
    data_list = []
    source_path = ''

    for file_found in files_found:
        source_path = str(file_found)
        if not source_path.lower().endswith(".txt"):
            continue
            
        txt = TXTFile(source_path)
        
        try:
            for record in txt.ParseRecord():
                record_time, longitude, latitude, height = record[0], record[1], record[2], record[4]
                data_list.append((record_time, longitude, latitude, height))
        except (ValueError, KeyError, IndexError, struct.error): 
            continue
        except Exception: 
            continue
            
    data_headers = ('Timestamp', 'Longitude', 'Latitude', 'Height')
    return data_headers, data_list, source_path

class OutOfDataException(Exception):
    pass

class Eater:
    def __init__(self, data):
        self._data = data
        self._cur = 0
    def read_data(self, size):
        if self._cur + size >= len(self._data):
            raise OutOfDataException()
        self._cur += size
        return self._data[self._cur-size:self._cur]
    def skip(self, size):
        self._cur += size
    def read_string(self, size):
        return self.read_data(size).rstrip(b"\x00").decode("utf-8", errors="ignore")
    def read_uint8(self):
        return struct.unpack("<B", self.read_data(1))[0]
    def read_uint32(self):
        return struct.unpack("<I", self.read_data(4))[0]
    def read_uint64(self):
        return struct.unpack("<Q", self.read_data(8))[0]
    def read_float(self):
        return struct.unpack("<f", self.read_data(4))[0]
    def read_double(self):
        return struct.unpack("<d", self.read_data(8))[0]

crc64Table = [
    0x0, 0x7AD870C830358979, 0xF5B0E190606B12F2, 0x8F689158505E9B8B,
    0xC038E5739841B68F, 0xBAE095BBA8743FF6, 0x358804E3F82AA47D,
    0x4F50742BC81F2D04, 0xAB28ECB46814FE75, 0xD1F09C7C5821770C,
    0x5E980D24087FEC87, 0x24407DEC384A65FE, 0x6B1009C7F05548FA,
    0x11C8790FC060C183, 0x9EA0E857903E5A08, 0xE478989FA00BD371,
    0x7D08FF3B88BE6F81, 0x7D08FF3B88BE6F8, 0x88B81EABE8D57D73,
    0xF2606E63D8E0F40A, 0xBD301A4810FFD90E, 0xC7E86A8020CA5077,
    0x4880FBD87094CBFC, 0x32588B1040A14285, 0xD620138FE0AA91F4,
    0xACF86347D09F188D, 0x2390F21F80C18306, 0x594882D7B0F40A7F,
    0x1618F6FC78EB277B, 0x6CC0863448DEAE02, 0xE3A8176C18803589,
    0x997067A428B5BCF0, 0xFA11FE77117CDF02, 0x80C98EBF2149567B,
    0xFA11FE77117CDF0, 0x75796F2F41224489, 0x3A291B04893D698D,
    0x40F16BCCB908E0F4, 0xCF99FA94E9567B7F, 0xB5418A5CD963F206,
    0x513912C379682177, 0x2BE1620B495DA80E, 0xA489F35319033385,
    0xDE51839B2936BAFC, 0x9101F7B0E12997F8, 0xEBD98778D11C1E81,
    0x64B116208142850A, 0x1E6966E8B1770C73, 0x8719014C99C2B083,
    0xFDC17184A9F739FA, 0x72A9E0DCF9A9A271, 0x8719014C99C2B08,
    0x4721E43F0183060C, 0x3DF994F731B68F75, 0xB29105AF61E814FE,
    0xC849756751DD9D87, 0x2C31EDF8F1D64EF6, 0x56E99D30C1E3C78F,
    0xD9810C6891BD5C04, 0xA3597CA0A188D57D, 0xEC09088B6997F879,
    0x96D1784359A27100, 0x19B9E91B09FCEA8B, 0x636199D339C963F2,
    0xDF7ADABD7A6E2D6F, 0xA5A2AA754A5BA416, 0x2ACA3B2D1A053F9D,
    0x50124BE52A30B6E4, 0x1F423FCEE22F9BE0, 0x659A4F06D21A1299,
    0xEAF2DE5E82448912, 0x902AAE96B271006B, 0x74523609127AD31A,
    0xE8A46C1224F5A63, 0x81E2D7997211C1E8, 0xFB3AA75142244891,
    0xB46AD37A8A3B6595, 0xCEB2A3B2BA0EECEC, 0x41DA32EAEA507767,
    0x3B024222DA65FE1E, 0xA2722586F2D042EE, 0xD8AA554EC2E5CB97,
    0x57C2C41692BB501C, 0x2D1AB4DEA28ED965, 0x624AC0F56A91F461,
    0x1892B03D5AA47D18, 0x97FA21650AFAE693, 0xED2251AD3ACF6FEA,
    0x95AC9329AC4BC9B, 0x7382B9FAAAF135E2, 0xFCEA28A2FAAFAE69,
    0x8632586ACA9A2710, 0xC9622C4102850A14, 0xB3BA5C8932B0836D,
    0x3CD2CDD162EE18E6, 0x460ABD1952DB919F, 0x256B24CA6B12F26D,
    0x5FB354025B277B14, 0xD0DBC55A0B79E09F, 0xAA03B5923B4C69E6,
    0xE553C1B9F35344E2, 0x9F8BB171C366CD9B, 0x10E3202993385610,
    0x6A3B50E1A30DDF69, 0x8E43C87E03060C18, 0xF49BB8B633338561,
    0x7BF329EE636D1EEA, 0x12B592653589793, 0x4E7B2D0D9B47BA97,
    0x34A35DC5AB7233EE, 0xBBCBCC9DFB2CA865, 0xC113BC55CB19211C,
    0x5863DBF1E3AC9DEC, 0x22BBAB39D3991495, 0xADD33A6183C78F1E,
    0xD70B4AA9B3F20667, 0x985B3E827BED2B63, 0xE2834E4A4BD8A21A,
    0x6DEBDF121B863991, 0x1733AFDA2BB3B0E8, 0xF34B37458BB86399,
    0x8993478DBB8DEAE0, 0x6FBD6D5EBD3716B, 0x7C23A61DDBE6F812,
    0x3373D23613F9D516, 0x49ABA2FE23CC5C6F, 0xC6C333A67392C7E4,
    0xBC1B436E43A74E9D, 0x95AC9329AC4BC9B5, 0xEF74E3E19C7E40CC,
    0x601C72B9CC20DB47, 0x1AC40271FC15523E, 0x5594765A340A7F3A,
    0x2F4C0692043FF643, 0xA02497CA54616DC8, 0xDAFCE7026454E4B1,
    0x3E847F9DC45F37C0, 0x445C0F55F46ABEB9, 0xCB349E0DA4342532,
    0xB1ECEEC59401AC4B, 0xFEBC9AEE5C1E814F, 0x8464EA266C2B0836,
    0xB0C7B7E3C7593BD, 0x71D40BB60C401AC4, 0xE8A46C1224F5A634,
    0x927C1CDA14C02F4D, 0x1D148D82449EB4C6, 0x67CCFD4A74AB3DBF,
    0x289C8961BCB410BB, 0x5244F9A98C8199C2, 0xDD2C68F1DCDF0249,
    0xA7F41839ECEA8B30, 0x438C80A64CE15841, 0x3954F06E7CD4D138,
    0xB63C61362C8A4AB3, 0xCCE411FE1CBFC3CA, 0x83B465D5D4A0EECE,
    0xF96C151DE49567B7, 0x76048445B4CBFC3C, 0xCDCF48D84FE7545,
    0x6FBD6D5EBD3716B7, 0x15651D968D029FCE, 0x9A0D8CCEDD5C0445,
    0xE0D5FC06ED698D3C, 0xAF85882D2576A038, 0xD55DF8E515432941,
    0x5A3569BD451DB2CA, 0x20ED197575283BB3, 0xC49581EAD523E8C2,
    0xBE4DF122E51661BB, 0x3125607AB548FA30, 0x4BFD10B2857D7349,
    0x4AD64994D625E4D, 0x7E7514517D57D734, 0xF11D85092D094CBF,
    0x8BC5F5C11D3CC5C6, 0x12B5926535897936, 0x686DE2AD05BCF04F,
    0xE70573F555E26BC4, 0x9DDD033D65D7E2BD, 0xD28D7716ADC8CFB9,
    0xA85507DE9DFD46C0, 0x273D9686CDA3DD4B, 0x5DE5E64EFD965432,
    0xB99D7ED15D9D8743, 0xC3450E196DA80E3A, 0x4C2D9F413DF695B1,
    0x36F5EF890DC31CC8, 0x79A59BA2C5DC31CC, 0x37DEB6AF5E9B8B5,
    0x8C157A32A5B7233E, 0xF6CD0AFA9582AA47, 0x4AD64994D625E4DA,
    0x300E395CE6106DA3, 0xBF66A804B64EF628, 0xC5BED8CC867B7F51,
    0x8AEEACE74E645255, 0xF036DC2F7E51DB2C, 0x7F5E4D772E0F40A7,
    0x5863DBF1E3AC9DE, 0xE1FEA520BE311AAF, 0x9B26D5E88E0493D6,
    0x144E44B0DE5A085D, 0x6E963478EE6F8124, 0x21C640532670AC20,
    0x5B1E309B16452559, 0xD476A1C3461BBED2, 0xAEAED10B762E37AB,
    0x37DEB6AF5E9B8B5B, 0x4D06C6676EAE0222, 0xC26E573F3EF099A9,
    0xB8B627F70EC510D0, 0xF7E653DCC6DA3DD4, 0x8D3E2314F6EFB4AD,
    0x256B24CA6B12F26, 0x788EC2849684A65F, 0x9CF65A1B368F752E,
    0xE62E2AD306BAFC57, 0x6946BB8B56E467DC, 0x139ECB4366D1EEA5,
    0x5CCEBF68AECEC3A1, 0x2616CFA09EFB4AD8, 0xA97E5EF8CEA5D153,
    0xD3A62E30FE90582A, 0xB0C7B7E3C7593BD8, 0xCA1FC72BF76CB2A1,
    0x45775673A732292A, 0x3FAF26BB9707A053, 0x70FF52905F188D57,
    0xA2722586F2D042E, 0x854FB3003F739FA5, 0xFF97C3C80F4616DC,
    0x1BEF5B57AF4DC5AD, 0x61372B9F9F784CD4, 0xEE5FBAC7CF26D75F,
    0x9487CA0FFF135E26, 0xDBD7BE24370C7322, 0xA10FCEEC0739FA5B,
    0x2E675FB4576761D0, 0x54BF2F7C6752E8A9, 0xCDCF48D84FE75459,
    0xB71738107FD2DD20, 0x387FA9482F8C46AB, 0x42A7D9801FB9CFD2,
    0xDF7ADABD7A6E2D6, 0x772FDD63E7936BAF, 0xF8474C3BB7CDF024,
    0x829F3CF387F8795D, 0x66E7A46C27F3AA2C, 0x1C3FD4A417C62355,
    0x935745FC4798B8DE, 0xE98F353477AD31A7, 0xA6DF411FBFB21CA3,
    0xDC0731D78F8795DA, 0x536FA08FDFD90E51, 0x29B7D047EFEC8728
]

def crc64(seed, buffer):
    crc = seed
    for i in buffer:
        tableIndex = i ^ (crc & 0xFF)
        crc = crc64Table[tableIndex] ^ (crc >> 8)
    return crc

class RecordType(Enum):
    OSD = 0x01
    HOME = 0x02
    GIMBAL = 0x03
    RC = 0x04
    CUSTOM = 0x05
    DEFORM = 0x06
    CENTER_BATTERY = 0x07
    SMART_BATTERY = 0x08
    APP_TIP = 0x09
    APP_WARN = 0x0A
    RC_GPS = 0x0B
    RC_DEBUG = 0x0C
    RECOVER = 0x0D
    APP_GPS = 0x0E
    FIRMWARE = 0x0F
    OFDM_DEBUG = 0x10
    VISION_GROUP = 0x11
    VISION_WARN = 0x12
    MC_PARAM = 0x13
    APP_OPERATION = 0x14
    APP_SER_WARN = 0x18
    COMPONENT = 0x28
    JPEG = 0x39
    OTHER = 0xFE

def GetScrambleBytes(record_type, key_byte):
    data_for_buffer = (0x123456789ABCDEF0 * key_byte) & 0xFFFFFFFFFFFFFFFF
    buffer_to_crc = struct.pack("<Q", data_for_buffer)
    return struct.pack("<Q", crc64((record_type + key_byte) & 0xFF, buffer_to_crc))

def ParseCustom(data):
    _, _, update_time = struct.unpack("<ffQ", data[2:18])
    return [datetime.fromtimestamp(update_time / 1000)]

def ParseOSD(data):
    longitude, latitude, height, _, _, _ = struct.unpack("<ddhhhh", data[:24])
    return [longitude * (180 / math.pi), latitude * (180 / math.pi), height]

class TXTFile:
    def __init__(self, path):
        with open(path, "rb") as f:
            self.data = f.read()
        self.header_size = 100
        self.is_scrambled = True
        self.records_start = 0
        self.records_end, self.details_size, self.version = struct.unpack("<QHB", self.data[:11])
        if self.version < 0x06:
            self.header_size = 12
            self.is_scrambled = False
        if self.version >= 0x0C:
            self.records_start = self.header_size + self.details_size
            self.details_start = self.header_size
            self.details_end = self.details_start + self.details_size
        else:
            self.records_start = self.header_size
            self.details_start = self.records_end
            self.details_end = self.details_start + self.details_size
            
    def ParseRecord(self):
        data = self.data[self.records_start:self.records_end]
        cur_idx = 0
        location_records = []
        last_gps = None
        while cur_idx < len(data):
            try:
                r_type = data[cur_idx]
                r_len = data[cur_idx+1]
                cur_idx += 2
                if r_type == RecordType.JPEG.value or (r_type == 0xFF and r_len == 0xD8):    
                    break 
                if data[cur_idx+r_len] != 0xFF:
                    if data[cur_idx+r_len+1] == 0xFF:
                        r_len += 1
                    else:
                        break
                if self.is_scrambled:
                    scramble = GetScrambleBytes(r_type, data[cur_idx])
                    raw = data[cur_idx+1:cur_idx+r_len]
                    unscrambled = bytes([(i ^ scramble[index % 8]) for index, i in enumerate(raw)])
                    record_data = unscrambled
                else:
                    record_data = data[cur_idx:cur_idx+r_len]
                if r_type == RecordType.CUSTOM.value:
                    custom_data = ParseCustom(record_data)
                    if last_gps:
                        location_records.append([custom_data[0], last_gps[0], last_gps[1], 0, last_gps[2]])
                elif r_type == RecordType.OSD.value:
                    last_gps = ParseOSD(record_data)
                
                cur_idx += (r_len + 1)
            except Exception:
                break
        return location_records

    def ParseDetail(self):
        data = self.data[self.details_start:self.details_end]
        detail = {}
        eater = Eater(data)
        try:
            eater.skip(80)
            detail["timestamp"] = eater.read_uint64()
        except (OutOfDataException, struct.error):
            pass
        except Exception:
            pass
        return detail

