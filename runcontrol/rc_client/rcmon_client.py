#!/usr/bin/env python3
#coding=utf-8

import asyncio
import websockets
import datetime

import argparse
import sys

import time
import json

from cmd2.table_creator import (
    Column,
    SimpleTable,
    HorizontalAlignment
)

from typing import (
    List,
)

from rc_exp import RC

"""Parse command line arguments"""
def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dev", action="store", type=str, help="device to open (default: /dev/uio0)", default="/dev/uio0")
    parser.add_argument("--ip", action="store", type=str, help="ip of the server (default: 172.16.24.10)", default="172.16.24.10")
    parser.add_argument("--freq", action="store", type=int, help="monitoring frequency (default: 1 second)", default=1)
    parser.add_argument("--reg", help='comma-separated list of registers to monitor', required=True)
    parser.add_argument("-f", "--filename", action="store", type=str, help="output filename")
    parser.add_argument('-l', '--filelabel', action='store', type=str, help='output filename <label>-<YYYYMMDD>-<HHMM>.csv')
    return parser.parse_args()

"""Setup the table with column headers"""
def setup_table():
    columns: List[Column] = [
        Column("time", width=20, data_horiz_align=HorizontalAlignment.CENTER),
        Column("register", width=12, data_horiz_align=HorizontalAlignment.CENTER),
        Column("hex_value", width=12, data_horiz_align=HorizontalAlignment.CENTER),
        Column("int_value", width=12, data_horiz_align=HorizontalAlignment.CENTER)
    ]
    return SimpleTable(columns, divider_char=None)


def header():
    print(setup_table().generate_data_row(["time", "register", "hex_value", "int_value"]))

async def send_data():
    args = parse_args()

    uri = f"ws://{args.ip}:8001"
    async with websockets.connect(uri) as websocket:

        

        config = {
                "type": "config",
                "frequency" : args.freq,
                "filename" : args.filename,
                "filelable" : args.filelabel

            }
        
        message = json.dumps(config)

        await websocket.send(message)

        ack_message = await websocket.recv()
        ack_data = json.loads(ack_message)

        if ack_data.get("type") == "ack" and ack_data.get("status") == "ready":
            print("Server is ready. Starting data transmission.")

        try:
            rcModList = [int(x) for x in args.reg.split(",")]
        except ValueError:
            print('E: failed to parse --reg - should be comma-separated list of integers')
            sys.exit(-1)

        rc = RC()

        header()

        try:
            while True:
                start = time.time()
                for i in rcModList:
                    reg = rc.read(str(i))
                    row = {
                        "type": "data",
                        "time": datetime.datetime.now().isoformat(),
                        "register": i,
                        "hex_value": reg[0],
                        "int_value": reg[1]
                    }

                    reg_data = json.dumps(row)
                    await websocket.send(reg_data)

                    
                    print(setup_table().generate_data_row([datetime.datetime.now().isoformat(), i, reg[0], reg[1]]))
                
                stop = time.time()
                delta = stop - start
                await asyncio.sleep(args.freq - delta)
                header()

        except KeyboardInterrupt:
            pass

        except websockets.exceptions.ConnectionClosedOK:
            print("Connection closed normally.")


        
        
        


if __name__ == "__main__":
    asyncio.run(send_data())