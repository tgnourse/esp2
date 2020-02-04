import serial
import pprint
import binascii
from influxdb import InfluxDBClient
import argparse


def parse_decimal_field(data):
    return float(parse_field(data)) / 10


# Parses a decimal field
def parse_field(data):
    m = {
        176: '0',  # B0
        177: '1',
        178: '2',
        179: '3',
        180: '4',
        181: '5',
        182: '6',
        183: '7',
        184: '8',
        185: '9',
        48: '0',  # 30
        49: '1',
        50: '2',
        51: '3',
        52: '4',
        53: '5',
        54: '6',
        55: '7',
        56: '8',
        57: '9',
    }
    f = ''
    for b in data:
        if b in m:
            f = f + m[b]
        else:
            f = f + '#'
    return f


def parse_meter(data):
    print('length: ' + str(len(data)))
    # print(data.hex())
    return {
        'model_number': binascii.hexlify(data[1:3]),
        'version': binascii.hexlify(data[3:4]),
        'address': parse_field(data[4:16]),
        'kwh_total': parse_decimal_field(data[16:24]),
        'kwh_t1': parse_decimal_field(data[24:32]),
        'kwh_t2': parse_decimal_field(data[32:40]),
        'kwh_t3': parse_decimal_field(data[40:48]),
        'kwh_t4': parse_decimal_field(data[48:56]),
        'kwh_total_reverse': parse_decimal_field(data[56:64]),
        'kwh_t1_reverse': parse_decimal_field(data[64:72]),
        'kwh_t2_reverse': parse_decimal_field(data[72:80]),
        'kwh_t3_reverse': parse_decimal_field(data[80:88]),
        'kwh_t4_reverse': parse_decimal_field(data[88:96]),
        'volts_l1_l2': parse_decimal_field(data[96:100]),
        'volts_l2_l3': parse_decimal_field(data[100:104]),
        'volts_l3_l1': parse_decimal_field(data[104:108]),
        'amps_l1': parse_decimal_field(data[108:112]),
        'amps_l2': parse_decimal_field(data[112:116]),
        'amps_l3': parse_decimal_field(data[116:120]),
        # TODO: Not 100% sure this is the right parsing of this data.
        'watts_phase_1': parse_decimal_field(data[126:132]),
        'watts_phase_2': parse_decimal_field(data[132:138]),
        'watts_phase_3': parse_decimal_field(data[138:144]),
        'watts_total': parse_decimal_field(data[120:126]),
        # TODO: Below here's not working, data doesn't seem to line up.
        # 'power_factor_phase_1': parse_field(data[144:148]),
        # 'power_factor_phase_2': parse_field(data[148:152]),
        # 'power_factor_phase_3': parse_field(data[152:156]),
        # 'demand_max': parse_field(data[156:162]),
        # 'demand_period': parse_field(data[162:163]),
        # 'date_year': parse_field(data[163:165]),
        # 'date_month': parse_field(data[165:167]),
        # 'date_day': parse_field(data[167:169]),
        # 'date_day_of_week': parse_field(data[169:171]),
        # 'time_hour': parse_field(data[171:173]),
        # 'time_minute': parse_field(data[173:175]),
        # 'time_second': parse_field(data[175:177]),
    }


def read_meters(port, ids):
    ser = serial.Serial(port)
    print(ser.name)

    results = []
    for meter_id in ids:
        print('reading: ' + meter_id)
        ser.write(b'/?' + meter_id.encode('ascii') + b'!\r\n')
        results.append(parse_meter(ser.read(255)))

    ser.close()
    return results


def transform_point(response):
    return {
        'measurement': 'readings',
        'tags': {
            'address': response['address'],
            'model_number': response['model_number'],
            'version': response['version'],
        },
        'fields': {
            'kwh_total': response['kwh_total'],
            'kwh_t1': response['kwh_t1'],
            'kwh_t2': response['kwh_t2'],
            'kwh_t3': response['kwh_t3'],
            'kwh_t4': response['kwh_t4'],
            'kwh_total_reverse': response['kwh_total_reverse'],
            'kwh_t1_reverse': response['kwh_t1_reverse'],
            'kwh_t2_reverse': response['kwh_t2_reverse'],
            'kwh_t3_reverse': response['kwh_t3_reverse'],
            'kwh_t4_reverse': response['kwh_t4_reverse'],
            'volts_l1_l2': response['volts_l1_l2'],
            'volts_l2_l3': response['volts_l2_l3'],
            'volts_l3_l1': response['volts_l3_l1'],
            'amps_l1': response['amps_l1'],
            'amps_l2': response['amps_l2'],
            'amps_l3': response['amps_l3'],
            'watts_phase_1': response['watts_phase_1'],
            'watts_phase_2': response['watts_phase_2'],
            'watts_phase_3': response['watts_phase_3'],
            'watts_total': response['watts_total'],
        }
    }


def transform_points(responses):
    points = []
    for response in responses:
        points.append(transform_point(response))
    return points


def upload_data(host, port, user, password, dbname, data):
    print('Uploading this data:\n')
    pprint.pprint(data)
    print('to ' + user + '@' + host + ':'+ port + '/' + dbname)
    client = InfluxDBClient(host, port, user, password, dbname, ssl=True, verify_ssl=False)
    return client.write_points(data)


def collect_and_upload(serial_port, meters, host, port, user, password, database):
    responses = read_meters(serial_port, meters)
    upload_data(host, port, user, password, database, transform_points(responses))


def test_parsing():
    # 000400003705
    meter1 = b'\x82\x90"\x17000\xb400003\xb705000\xb13\xb1\xb1\xb70000\xb80600000505\xb700000000000000000000000000000000000000000000000000000000\xb1\xb2\xb20\xb1\xb2\xb1\xb7000000000000360000000000\xb1\xb4000036\xb2000000000003\xb7\xb8\xc3099\xcc099\xc3000000\xb23\xb400\xb1\xb200\xb2030\xb2\xb1\xb209\xb2\xb10\xb2000000000000000000000000000000000000000000000000000000000000\x00!\x8d\n\x03`\xc0'
    print(meter1)
    print(meter1.hex())

    it = iter(meter1.hex())
    for b1 in it:
        print(next(it), end="")
    print('')
    # 000400003718
    meter2 = b'\x82\x90"\x17000\xb400003\xb7\xb1\xb8000035050000\xb2\xb1\xb8\xb80000\xb13\xb1\xb700000000000000000000000000000000000000000000000000000000\xb1\xb2\xb1900000000000\xb1000000000000000\xb1\xb10000000000000000000\xb1\xb10\xc309\xb4\xc3000\xc30000000\xb2600\xb1\xb200\xb20\xb20\xb1\xb20\xb1\xb1\xb2\xb20\xb2000000000000000000000000000000000000000000000000000000000000\x00!\x8d\n\x03\x84\x81'

    pprint.pprint(parse_meter(meter1))
    pprint.pprint(parse_meter(meter2))


def test_reading():
    # on mac: /dev/tty.usbserial-141320
    pprint.pprint(read_meters('/dev/ttyUSB1', ['000400003705', '000400003718']))


def test_uploading(host, port, user, password, database):
    meter1 = b'\x82\x90"\x17000\xb400003\xb705000\xb13\xb1\xb1\xb70000\xb80600000505\xb700000000000000000000000000000000000000000000000000000000\xb1\xb2\xb20\xb1\xb2\xb1\xb7000000000000360000000000\xb1\xb4000036\xb2000000000003\xb7\xb8\xc3099\xcc099\xc3000000\xb23\xb400\xb1\xb200\xb2030\xb2\xb1\xb209\xb2\xb10\xb2000000000000000000000000000000000000000000000000000000000000\x00!\x8d\n\x03`\xc0'
    upload_data(host, port, user, password, database, transform_points([parse_meter(meter1)]))


parser = argparse.ArgumentParser()
parser.add_argument('--influxdb_host')
parser.add_argument('--influxdb_port', type=int, default=8086)
parser.add_argument('--influxdb_user')
parser.add_argument('--influxdb_password')
parser.add_argument('--influxdb_database')
parser.add_argument('--serial_port', default='/dev/ttyUSB1')
parser.add_argument('meters', nargs='+')
args = parser.parse_args()

collect_and_upload(
    args.serial_port, args.meters,
    args.influxdb_host, args.influxdb_port, args.influxdb_user, args.influxdb_password, args.influxdb_database)

# test_uploading(args.influxdb_host, args.influxdb_port, args.influxdb_user, args.influxdb_password, args.influxdb_database)
# test_parsing()
# test_reading()
