#!/usr/bin/env python3
#coding=utf-8

import zmq
import argparse
import time
import json
from rc_conf import RC

rc = RC()

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", action="store", type=str, help="ip of the server (default: 172.16.24.10)", default="172.16.24.10")
    return parser.parse_args()


args = parse_args()

PING_INTERVAL = 6 #Ogni quanti secondi viene inviato il messaggio di ping
PING_TIMEOUT = 10

def client():

    server_address = f"tcp://{args.ip}:8005"
    #server_address = f"tcp://{args.ip}:8005"

    context = zmq.Context()

    connection_socket = context.socket(zmq.DEALER)
    connection_socket.setsockopt(zmq.IDENTITY, b"RC")

    print("Connecting to server...")
    connection_socket.connect(server_address)

    poller = zmq.Poller()
    poller.register(connection_socket, zmq.POLLIN)

    last_ping = time.time()
    while True:

        try:
            if time.time() - last_ping >= PING_INTERVAL:
                #print("Ping signal sent")
                connection_socket.send(b"Ping")
                last_ping = time.time()
            
            socks = dict(poller.poll(PING_TIMEOUT * 1000))
            if socks.get(connection_socket) == zmq.POLLIN:
                message = connection_socket.recv()
                if message == b"Alive":
                    print("Server responded and is connected")
                    connection_socket.send(b"Connection successful")
                    connected = True

                    while connected:
                        connected = handle_commands(connection_socket)


            else:
                #print("No response from server. Reconnecting...")
                time.sleep(PING_INTERVAL)
                connection_socket.disconnect(server_address)
                connection_socket.connect(server_address)

        except zmq.ZMQError as e:
            print(f"ZeroMQ Error: {e}")
            break

        except KeyboardInterrupt:
            print("Client interrupted. Shutting down...")
            break


def receive_json(socket): 

    try: 
        return json.loads(socket.recv()) 
    except json.JSONDecodeError: 
        print("Error decoding JSON message") 
        return None
    
def send_json(socket, data): 

    try: 
        return socket.send(json.dumps(data).encode("utf-8"))
    except json.JSONDecodeError: 
        print("Error decoding JSON message") 
        return None


def handle_commands(socket):
    """
    Handle messages based on the command from the server.
    """
    server_command = receive_json(socket)
    if server_command is None:
        print("Something went wrong sending the commands to the client")
        return True


    elif server_command.get("type") == "clients":
        command_back = server_command.get("command")
        if command_back == "back":
            return False
        
    elif server_command.get("type") == "rc_command":
        command = server_command.get("command")
        if command == "read_address":
            read = {

                "response" : "rc_read",
                "result" : rc.read(server_command.get("address"))
                    
                    }
            send_json(socket, read)

        
        if command == "write_address":
            addr = server_command.get("address")
            value = server_command.get("value")
            if rc.write(addr, value):
                write_t = {
                    "response" : "rc_write",
                    "result" : f"Successufully wrote the value {value} in register {addr}"
                }
                send_json(socket, write_t)

            else:
                write_f = {
                    "response" : "rc_write",
                    "result" : f"It was not possible to write the value {value} in register {addr}"
                }
                send_json(socket, write_f)

                

        if command == "rc_pwr_on":
            channels = server_command.get("channels")
            if rc.init_data(channels):
                pwr_on_t = {

                    "response" : "rc_power_on",
                    "result" : f"Successufully powered on the channels: {channels}"

                }
                send_json(socket, pwr_on_t)
            else:
                pwr_on_f = {

                    "response" : "rc_power_on",
                    "result" : f"It was not possible to power on the channels: {channels}"

                }
                send_json(socket, pwr_on_f)

            


        
    return True
    
             



if __name__== "__main__":
    client()
