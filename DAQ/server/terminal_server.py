import cmd2
import argparse
import zmq
import json
import time


context = zmq.Context()
control_socket = context.socket(zmq.ROUTER)
control_socket.bind("tcp://*:8005")


class ServerTerminal(cmd2.Cmd):

    "A terminal application to switch and interact with the clients on the MainBoard"

    intro  = "Welcome to the control interface of the multiPMT. Type ? or help to list commands."
    prompt = "|Main>"
    client = None

    def __init__(self,) -> None:
        super().__init__()


    client_parser = argparse.ArgumentParser()
    client_parser.add_argument("client", type=str, help="Selects the client")

    @cmd2.with_argparser(client_parser)
    @cmd2.with_category("Clients Selection")
    def do_connect(self, args: argparse.Namespace) -> None:
        """
        Select a specific client page and verify the connection with the client itself.
        Usage: connect <client_name>
        Example: connect RC
        """

        client_list = ["RC", "HV"]
        timeout = 10
        start_time = time.time()

        if args.client in client_list:
            client_id = args.client.encode("utf-8")
            connected = False
    
            while not connected and (time.time() - start_time < timeout):
                try:
                    client_id_received, information = control_socket.recv_multipart()

                    if client_id_received == client_id and information == b"Ping":
                        self.poutput("Ping signal received")
                        control_socket.send_multipart([client_id, b"Alive"])

                        response = control_socket.recv_multipart()
                        if response[0] == client_id and response[1] == b"Connection successful":
                            self.poutput(f"Connection was successful with client: {args.client}")
                            self.client = args.client
                            self.prompt = f"|{args.client}>"
                            connected = True
                    else:
                        self.poutput("It was not possible to connect with the client selected")

                except zmq.Again:
                    time.sleep(0.1)

        else:
            self.poutput(f"Invalid client name. Available clients: {client_list}")



    def _check_client(self, required_client):
        """
        Utility method to ensure the command is used in the correct client page.
        """
        if self.client != required_client:
            print(f"This command is only available in the {required_client} client page.")
            return False
        return True
    

    
    @cmd2.with_category("Clients Selection")
    def do_back(self, _) -> None:
        """
        Return to the main menu.
        """

        command_back = {

            "type" : "clients",
            "command" : "back"
        }


        control_socket.send_multipart([self.client.encode("utf-8"), json.dumps(command_back).encode("utf-8")])


        self.client = None
        self.prompt = "|Main>"
        self.poutput("Returned to the main menu")




    @cmd2.with_category("Generic Commands")
    def do_quit(self, _) -> None:
        """
        Quit from the application
        """
        if self.client:
            command_back = {

                "type" : "clients",
                "command" : "back"
            }


            control_socket.send_multipart([self.client.encode("utf-8"), json.dumps(command_back).encode("utf-8")])
            
        self.poutput("Quit command received. Shutting down...")
        return super().do_quit(_)




    
    print_message_rc = argparse.ArgumentParser()
    print_message_rc.add_argument("message", type=str, help="The message the client has to print")
    
    @cmd2.with_argparser(print_message_rc)
    @cmd2.with_category("RC")
    def do_print_message(self, args: argparse.Namespace) -> None:

        if self._check_client("RC"):
            command_print = {

                "type": "rc_config",
                "command": "print_message",
                "message": args.message

            }

            control_socket.send_multipart([self.client.encode("utf-8"), json.dumps(command_print).encode("utf-8")])


    print_message_hv = argparse.ArgumentParser()
    print_message_hv.add_argument("message", type=str, help="The message the client has to print")
    
    @cmd2.with_argparser(print_message_hv)
    @cmd2.with_category("HV")
    def do_print_message(self, args: argparse.Namespace) -> None:

        if self._check_client("HV"):
            command_print = {

                "type": "hv_config",
                "command": "print_message",
                "message": args.message

            }

            control_socket.send_multipart([self.client.encode("utf-8"), json.dumps(command_print).encode("utf-8")])


    

    

    rc_read = argparse.ArgumentParser()
    rc_read.add_argument("rc_register_address", type=int, help="The register of the Run Control intended to be read")


    @cmd2.with_argparser(rc_read)
    @cmd2.with_category("RC")
    def do_read(self, args: argparse.Namespace) -> None:
        """
        Function to read Run Control registers
        """

        if self._check_client("RC"):
            command_rc_read = {

                "type": "rc_command",
                "command": "read_address",
                "address": args.rc_register_address

            }

            control_socket.send_multipart([self.client.encode("utf-8"), json.dumps(command_rc_read).encode("utf-8")])
        
            read = control_socket.recv_multipart()

            try:
                response_data = json.loads(read[1].decode("utf-8"))

                if read[0] == b"RC" and response_data.get("response") == "rc_read":
                    print(f"The value of the register {args.rc_register_address} is: {response_data.get('result')[1]} ({response_data.get('result')[0]})")

            
            except json.JSONDecodeError:
                self.poutput("Failed to decode the response.")




    rc_write = argparse.ArgumentParser()
    rc_write.add_argument("rc_write_addr", type=int, help="The address of the register of the Run Control intended to be wrote")
    rc_write.add_argument("rc_write_value", type=int, help="The value intended to be wrote in the Run Control Register specified")


    @cmd2.with_argparser(rc_write)
    @cmd2.with_category("RC")
    def do_write(self, args: argparse.Namespace) -> None:
        "Function to write user specified values in the Run Control registers"

        if self._check_client("RC"):
            command_rc_write = {

                "type": "rc_command",
                "command": "write_address",
                "address": args.rc_write_addr,
                "value" : args.rc_write_value
            }


            control_socket.send_multipart([self.client.encode("utf-8"), json.dumps(command_rc_write).encode("utf-8")])
        
            write = control_socket.recv_multipart()

            try:
                response = json.loads(write[1].decode("utf-8"))
                if write[0] == b"RC" and response.get("response") == "rc_write":
                    print(response.get("result"))
                    
            except json.JSONDecodeError:
                self.poutput("Failed to decode the response.")



    rc_power_on = argparse.ArgumentParser()
    rc_power_on.add_argument("channels", type=str, help="Write all to power up all channels or the respectivly channel numbers")

    @cmd2.with_argparser(rc_power_on)
    @cmd2.with_category("RC")
    def do_power_on(self, args: argparse.Namespace) -> None:
        "Function to power on the channels selected"

        if self._check_client("RC"):
            command_rc_pwr_on = {

                "type": "rc_command",
                "command": "rc_pwr_on",
                "channels": args.channels

            }

            control_socket.send_multipart([self.client.encode("utf-8"), json.dumps(command_rc_pwr_on).encode("utf-8")])

            power_on = control_socket.recv_multipart()

            try:
                response_pwr = json.loads(power_on[1].decode("utf-8"))
                if power_on[0] == b"RC" and power_on.get("response") == "rc_power_on":
                    print(response_pwr.get("result"))
                    
            except json.JSONDecodeError:
                self.poutput("Failed to decode the response.")







if __name__ == '__main__':

    app = ServerTerminal()

    try:
        app.cmdloop()
    except KeyboardInterrupt:
        print("\n Shutting down...")
    finally:
        control_socket.close()
        context.term()
