#!/usr/bin/env python3
# coding=utf-8

import asyncio
import websockets
import datetime
import os
import sys
import csv
import json


"""Generate the output filename based on provided arguments"""
def generate_filename(config_information):
    if config_information.get("filename"):
        return config_information["filename"]
    
    elif config_information.get("filelabel"):
        d = datetime.datetime.now().strftime('%Y%m%d-%H%M')
        return f"{config_information['filelabel']}-{d}.csv"
    
    else:
        raise ValueError('E: filename (-f) or filelabel (-l) option is required')

"""Check if the file exists and prompt the user for action."""
def check_file_exists(fname):
    if os.path.exists(fname):
        while True:
            res = input(f'I: file {fname} exists - do you want overwrite (Y/N) ')
            if res.lower() in ["y", "yes"]:
                break
            elif res.lower() in ["n", "no"]:
                print("E: specify different filename")
                sys.exit(-1)


async def receive_data(websocket):


    config_information = await websocket.recv()
    command_information = json.loads(config_information)

    print(f"Received config: {command_information}")


    fname = generate_filename(command_information)
    check_file_exists(fname)

    ack_message = json.dumps({"type": "ack", "status": "ready"})
    await websocket.send(ack_message)


    with open(fname, "w", newline="") as file:

        keys_information = await websocket.recv()
        keys = json.loads(keys_information)

        writer = csv.DictWriter(file, fieldnames=keys, dialect='excel')
        writer.writeheader()

        ack_message2 = json.dumps({"type": "ack", "status": "ready"})
        await websocket.send(ack_message2)

        while True:

            try:
                message = await websocket.recv()
                data = json.loads(message)
                
                writer.writerow(data)
                file.flush()

            except websockets.exceptions.ConnectionClosedOK:
                print("Connection closed normally.")
                break

            except websockets.exceptions.ConnectionClosedError as e:
                print(f"Connection closed with error: {e}")
                break

            except Exception as e:
                print(f"Unexpected error: {e}")
                break

async def main():
    async with websockets.serve(receive_data, "0.0.0.0", 8002):
        await asyncio.Future() 


if __name__ == "__main__":
    asyncio.run(main())