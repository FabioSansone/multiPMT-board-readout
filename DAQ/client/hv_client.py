#!/usr/bin/env python3
#coding=utf-8


import zmq
import argparse
import time
import json
from hv_conf import HV

hv = HV()


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", action="store", type=str, help="ip of the server (default: 172.16.24.10)", default="172.16.24.10")
    return parser.parse_args()


args = parse_args()

PING_INTERVAL = 2 #Ogni quanti secondi viene inviato il messaggio di ping
PING_TIMEOUT = 5

def client():

    #server_address = "tcp://localhost:8005"
    server_address = f"tcp://{args.ip}:8006"

    context = zmq.Context()

    connection_socket = context.socket(zmq.DEALER)
    connection_socket.setsockopt(zmq.IDENTITY, b"HV")

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


def send_json(socket, data): 

    try: 
        return socket.send(json.dumps(data).encode("utf-8"))
    except json.JSONDecodeError: 
        print("Error decoding JSON message") 
        return None


def receive_json(socket): 

    try: 
        return json.loads(socket.recv()) 
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
    
    elif server_command.get("type") == "hv_command":
        command = server_command.get("command")

        if command == "set_init_configuration":
            port = server_command.get("port")
            channel = server_command.get("channel")
            voltage_set = server_command.get("voltage_set")    
            threshold_set = server_command.get("threshold_set")
            limit_trip_time = server_command.get("limit_trip_time")    
            limit_voltage = server_command.get("limit_voltage")
            limit_current = server_command.get("limit_current")
            limit_temperature = server_command.get("limit_temperature")
            rate_up = server_command.get("rate_up")
            rate_down = server_command.get("rate_down")

            init_conf = {

                "response" : "hv_init_conf",
                "result" : hv.set_hv_init_configuration(port, channel, voltage_set, threshold_set, limit_trip_time, limit_voltage, limit_current, limit_temperature, rate_up, rate_down)

            } 

            send_json(socket, init_conf)


        
        if command == "set_voltage":
            port = server_command.get("port")
            channel = server_command.get("channel")
            voltage_set = server_command.get("voltage_set")    

            v_set = {

                "response" : "hv_voltage_set",
                "result" : hv.set_voltage(channel, voltage_set, port)

            }

            send_json(socket, v_set)

        
        if command == "set_limitV":
            port = server_command.get("port")
            channel = server_command.get("channel")
            lim_voltage = server_command.get("lim_voltage")    

            v_lim = {

                "response" : "hv_voltage_limit",
                "result" : hv.set_limitV(channel, lim_voltage, port)

            }

            send_json(socket, v_lim)

        
        if command == "set_limitI":
            port = server_command.get("port")
            channel = server_command.get("channel")
            lim_current = server_command.get("lim_current")    

            i_lim = {

                "response" : "hv_current_limit",
                "result" : hv.set_limitI(channel, lim_current, port)

            }

            send_json(socket, i_lim)

        if command == "set_limitTrip":
            port = server_command.get("port")
            channel = server_command.get("channel")
            lim_trip = server_command.get("lim_triptime")    

            trip_lim = {

                "response" : "hv_triptime_limit",
                "result" : hv.set_limitTrip(channel, lim_trip, port)

            }

            send_json(socket, trip_lim)

        
        if command == "set_threshold":
            port = server_command.get("port")
            channel = server_command.get("channel")
            threshold = server_command.get("threshold")    

            set_threshold = {

                "response" : "hv_threshold",
                "result" : hv.set_threshold(channel, threshold, port)

            }

            send_json(socket, set_threshold)


        if command == "set_power_on":
            port = server_command.get("port")
            channel = server_command.get("channel")


            set_power_on = {

                "response": "hv_power_on",
                "result" : hv.power_on(channel, port)

            }

            send_json(socket, set_power_on)


        if command == "set_power_off":
            port = server_command.get("port")
            channel = server_command.get("channel")


            set_power_off = {

                "response": "hv_power_off",
                "result" : hv.power_off(channel, port)

            }

            send_json(socket, set_power_off)



    
        
    return True
    
             



if __name__== "__main__":
    client()
