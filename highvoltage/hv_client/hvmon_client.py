#!/usr/bin/env python3
#coding=utf-8

import asyncio
import websockets
import datetime
import argparse
import sys
import time
import json
import copy

from cmd2.table_creator import (
    Column,
    SimpleTable,
    HorizontalAlignment
)

from typing import (
    List,
)

from hvmodbus import HVModbus

def alarmString(alarmCode):
    msg = ' '
    if (alarmCode == 0):
        return 'none'
    if (alarmCode & 1):
        msg = msg + 'OV '
    if (alarmCode & 2):
        msg = msg + 'UV '
    if (alarmCode & 4):
        msg = msg + 'OC '
    if (alarmCode & 8):
        msg = msg + 'OT '
    return msg

def statusString(statusCode):
    if (statusCode == 0):
        return 'UP'
    elif (statusCode == 1):
        return 'DOWN'
    elif (statusCode == 2):
        return 'RUP'
    elif (statusCode == 3):
        return 'RDN'
    elif (statusCode == 4):
        return 'TUP'
    elif (statusCode == 5):
        return 'TDN'
    elif (statusCode == 6):
        return 'TRIP'
    else:
        return 'undef'


"""Parse command line arguments"""
def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', action='store', type=str, help='serial port device (default: /dev/ttyPS1)', default='/dev/ttyPS1')
    parser.add_argument('--ip', action='store', type=str, help='ip of the server (default: 172.16.24.10)', default='172.16.24.10')
    parser.add_argument('--freq', action='store', type=int, help='monitoring frequency (default: 1 second)', default=1)
    parser.add_argument('-m', '--modules', help='comma-separated list of modules to monitor', required=True)
    parser.add_argument('-f', '--filename', action='store', type=str, help='output filename')
    parser.add_argument('-l', '--filelabel', action='store', type=str, help='output filename <label>-<YYYYMMDD>-<HHMM>.csv')
    return parser.parse_args()

"""Setup the table with column headers"""
def setup_table():
    columns: List[Column] = [
        Column("", width=6, data_horiz_align=HorizontalAlignment.RIGHT),
        Column("", width=6, data_horiz_align=HorizontalAlignment.CENTER),
        Column("", width=5, data_horiz_align=HorizontalAlignment.RIGHT),
        Column("", width=9, data_horiz_align=HorizontalAlignment.RIGHT),
        Column("", width=7, data_horiz_align=HorizontalAlignment.RIGHT),
        Column("", width=7, data_horiz_align=HorizontalAlignment.RIGHT),
        Column("", width=12, data_horiz_align=HorizontalAlignment.RIGHT),
        Column("", width=20, data_horiz_align=HorizontalAlignment.RIGHT),
        Column("", width=13, data_horiz_align=HorizontalAlignment.RIGHT),
        Column("", width=14, data_horiz_align=HorizontalAlignment.CENTER)
    ]
    return SimpleTable(columns, divider_char=None)

def header():
    print(setup_table().generate_data_row(['addr','status','Vset','V','I','T','rate UP/DN','limit V/I/T/TRIP','trigger thr','alarm']))
    print(setup_table().generate_data_row(['','','[V]','[V]','[uA]','[°C]','[V/s]/[V/s]','[V]/[uA]/[°C]/[s]','[mV]','']))

def check_modules(hv_mod_list, port):
    hv_list = []
    for addr in hv_mod_list:
        hv = HVModbus()
        if hv.open(port, addr) != True:
            print(f'E: failed to open module {addr}')
            sys.exit(-1)
        else:
            hv_list.append(copy.copy(hv))
            print(f'I: module {addr} ok')
    return hv_list

def get_keys(hv):
    fields = list(hv.readMonRegisters().keys())
    fields.insert(0, 'timestamp')
    fields.insert(1, 'time')
    fields.insert(2, 'address')
    return fields



async def send_data():

    args = parse_args()

    uri = f"ws://{args.ip}:8002"
    async with websockets.connect(uri) as websocket:

        

        config = {
                "type": "config",
                "frequency" : args.freq,
                "filename" : args.filename,
                "filelable" : args.filelabel

            }
        
        config_message = json.dumps(config)
        await websocket.send(config_message)

        ack_message = await websocket.recv()
        ack_data = json.loads(ack_message)

        if ack_data.get("type") == "ack" and ack_data.get("status") == "ready":
            print("Server received config informtion")
        


        try:
            hvModList = [int(x) for x in args.modules.split(",")]
        except ValueError:
            print('E: failed to parse --reg - should be comma-separated list of integers')
            sys.exit(-1)
        
        hv_list = check_modules(hvModList, args.port)

        csv_message = json.dumps(get_keys(hv_list[0]))
        await websocket.send(csv_message)

        ack_message2 = await websocket.recv()
        ack_data2 = json.loads(ack_message2)

        if ack_data2.get("type") == "ack" and ack_data2.get("status") == "ready":
            print("Server received the keys")

        header()        

        try:
            i = 1
            while True:
                start = datetime.datetime.now()
                for hv in hv_list:
                    try:
                        mon = hv.readMonRegisters()
                    except Exception as e:
                        print(f'E: address {hv.address} - {e}')
                        continue
                    else:
                        mon['timestamp'] = int(time.time())
                        mon['time'] = datetime.datetime.now().strftime('%Y%m%d-%H%M')
                        mon['address'] = hv.address
                        mon['status'] = statusString(mon['status'])
                        mon['alarm'] = alarmString(mon['alarm'])
                        mon_data = json.dumps(mon)
                        await websocket.send(mon_data)
                        print(setup_table().generate_data_row([mon['address'], mon['status'], mon['Vset'], f'{mon["V"]:.3f}', f'{mon["I"]:.3f}', mon['T'], f'{mon["rateUP"]}/{mon["rateDN"]}', f'{mon["limitV"]}/{mon["limitI"]}/{mon["limitT"]}/{mon["limitTRIP"]}', mon['threshold'], mon['alarm']]))
                
                stop = datetime.datetime.now()
                delta = stop - start
                await asyncio.sleep(((args.freq * 1000) - (delta.total_seconds() * 1000)) / 1000)
                header()

        except KeyboardInterrupt:
            pass

if __name__ == "__main__":
    asyncio.run(send_data())
