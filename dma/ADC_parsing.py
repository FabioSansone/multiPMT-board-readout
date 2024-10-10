import multiprocessing
import zmq
import struct
import argparse
import os
import sys
import csv


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--filename', action='store', type=str, help='output filename', default="output.csv")
    return parser.parse_args()

def check_file_exists(fname):
    if os.path.exists(fname):
        while True:
            res = input(f'I: file {fname} exists - do you want overwrite (Y/N) ')
            if res.lower() in ["y", "yes"]:
                break
            elif res.lower() in ["n", "no"]:
                print("E: specify different filename")
                sys.exit(-1)

def string_no_space(string):
    return string.replace(" ", "")

def writer(filename, pipe_p):
    context = zmq.Context()
    frontend = context.socket(zmq.ROUTER) 
    frontend.bind("tcp://*:5555")
    
    with open(filename, "w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["DMA data row"], dialect='excel')
        writer.writeheader()
        
        try:
            while True:
                message = frontend.recv_multipart() 
                print("Message received")
                for part in message: 
                    if len(part) != 1:
                        l = int(len(part) / 2)
                        v = struct.unpack_from(f"{l}H", part) 
                        i = 0
                        a = ""
                        for b in v:
                            value = f'{b:04x} ' 
                            print(value, end='') 
                            i += 1
                            a += value
                            if i % 8 == 0: 
                                writer.writerow({"DMA data row": a.strip()})
                                file.flush()
                                pipe_p.send(a.strip())
                                a = ""
                                print("")
                                i = 0
            
                                    
    
        except KeyboardInterrupt:
            pass


def parser(filename, pipe_c):
    with open(filename + "_parsed", "w", newline="") as file_p:
        writer_p = csv.DictWriter(file_p, fieldnames=["Channel", "Unix_time_16_bit", "Coarse_time", "TDC_time", "ToT_time", "TDC_trigger_end", "Energy", "CRC"], dialect="excel")
        writer_p.writeheader()
        while True:
            event = pipe_c.recv()
            if not event:
                print("E: empty event received, ignoring the event")
                continue

            event = string_no_space(event)
            event_cut = event[4:-4]

            if not event_cut: 
                print("E: empty event received, ignoring the event")
                continue


            number_bits = len(event_cut) * 4
            event_integer = int(event_cut, 16)

            binary_string = bin(event_integer)[2:]
            event_bit = binary_string.zfill(number_bits)
            

            canale = event_bit[3:8]
            tempo_16_bit = event_bit[8:24]
            coarse_time = event_bit[24:32] + event_bit[33:40] + event_bit[40:53]
            tot = event_bit[53:59]
            tdc_trigger_end = event_bit[59:64]
            tdc_time = event_bit[69:74]
            energia = event_bit[74:88]
            crc = event_bit[88:96]

            writer_p.writerow({
                "Channel": canale,
                "Unix_time_16_bit": tempo_16_bit,
                "Coarse_time": coarse_time,
                "TDC_time": tdc_time,
                "ToT_time": tot,
                "TDC_trigger_end": tdc_trigger_end,
                "Energy": energia,
                "CRC": crc
            })

            file_p.flush()  


if __name__ == "__main__":
    args = parse_args()
    check_file_exists(args.filename)
    
    parent_pipe, child_pipe = multiprocessing.Pipe()

    writing = multiprocessing.Process(target=writer, args=(args.filename, parent_pipe,))
    parsing = multiprocessing.Process(target=parser, args=(args.filename, child_pipe,))

    writing.start()
    parsing.start()

    writing.join() 
    parsing.join()

    print("Both processes finished.")
