import zmq
import argparse
import time
import json


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", action="store", type=str, help="ip of the server (default: 172.16.24.10)", default="172.16.24.10")
    return parser.parse_args()


args = parse_args()

PING_INTERVAL = 2 #Ogni quanti secondi viene inviato il messaggio di ping
PING_TIMEOUT = 5

def client():

    server_address = "tcp://localhost:8005"
    #server_address = f"tcp://{args.ip}:8005"

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
                print("Ping signal sent")
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
                print("No response from server. Reconnecting...")
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

    
        
    return True
    
             



if __name__== "__main__":
    client()
