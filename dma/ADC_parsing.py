import multiprocessing
import zmq
import struct
import argparse
import os
import sys
import csv
import time

def get_time():
    return time.strftime("%Y_%m_%d_%H", time.gmtime(time.time()))

def get_file_name(time_info, name_file, suffix = ""):
    return str(name_file) + "_" + str(time_info) + suffix + ".csv"



def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--filename', action='store', type=str, help='output filename', default="output")
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
                try:
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
                                    try:
                                        writer.writerow({"DMA data row": a.strip()})
                                        file.flush()
                                        pipe_p.send(a.strip())
                                        a = ""
                                        print("")
                                        i = 0
                                    except Exception as e:
                                        print(f"It was not possible to write the data on the file: {e}")
                except Exception as e:
                    print(f"It was not possible to receive data from the ADC: {e}")
            
                                    
    
        except KeyboardInterrupt:
            pass

        finally:
            frontend.close()
            context.term()
            file.close()


def parser(filename, pipe_c):
    with open(filename, "w", newline="") as file_p:
        writer_p = csv.DictWriter(file_p, fieldnames=["Channel", "Unix_time_16_bit", "Coarse_time", "TDC_time", "ToT_time", "TDC_trigger_end", "Energy", "CRC"], dialect="excel")
        writer_p.writeheader()
        while True:
            try:
                event = pipe_c.recv()
                if not event:
                    print("E: evento vuoto ricevuto, interrompendo il parsing")
                    continue

                event = string_no_space(event)
                event_cut = event[4:-4]

                if not event_cut: 
                    print("E: event_cut è vuoto, ignorando l'evento")
                    continue 


                number_bits = len(event_cut) * 4
                event_integer = int(event_cut, 16)

                binary_string = bin(event_integer)[2:]
                event_bit = binary_string.zfill(number_bits)
                

                canale = int(event_bit[3:8],2)
                tempo_16_bit = int(event_bit[8:24],2)
                coarse_time = int(event_bit[24:32] + event_bit[33:40] + event_bit[40:53], 2)
                tot = int(event_bit[53:59], 2)
                tdc_trigger_end = int(event_bit[59:64], 2)
                tdc_time = int(event_bit[69:74], 2)
                energia = int(event_bit[74:88], 2)
                crc = int(event_bit[88:96], 2)

                try:
                    writer_p.writerow({
                        "Channel": str(canale),
                        "Unix_time_16_bit": str(tempo_16_bit),
                        "Coarse_time": str(coarse_time),
                        "TDC_time": str(tdc_time),
                        "ToT_time": str(tot),
                        "TDC_trigger_end": str(tdc_trigger_end),
                        "Energy": str(energia),
                        "CRC": str(crc)
                    })

                    file_p.flush() 

                except Exception as e:
                    print(f"It was not possible to write  the data on the file: {e}")
            
            except Exception as e:
                print(f"Something went wrong in the communication between the two processes : {e}")

        


if __name__ == "__main__":

    args = parse_args()

    file_n = get_file_name(get_time(), args.filename)
    check_file_exists(file_n)

    file_n_parsed = get_file_name(get_time(), args.filename, "_parsed")
    check_file_exists(file_n_parsed)
    
    parent_pipe, child_pipe = multiprocessing.Pipe()

    writing = multiprocessing.Process(target=writer, args=(file_n, parent_pipe,))
    parsing = multiprocessing.Process(target=parser, args=(file_n_parsed, child_pipe,))

    try:
        writing.start()
        parsing.start()

        writing.join() 
        parsing.join()
    
    finally:
        if writing.is_alive():
            writing.terminate()
        
        if parsing.is_alive():
            parsing.terminate()

    print("Both processes finished.")
