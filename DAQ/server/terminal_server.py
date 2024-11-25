import cmd2
import argparse
import zmq
import json
import time


context = zmq.Context()
control_socket = context.socket(zmq.ROUTER)
control_socket.bind("tcp://*:8005")

maxRegisterAddress_RC = 50


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


    #########################################################################
    # RC Commands #
    #########################################################################

    

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
                    if response_data.get("result"):
                        print(f"The value of the register {args.rc_register_address} is: {response_data.get('result')[1]} ({response_data.get('result')[0]})")
                    else:
                        print(f"Register address outside boundary - min:0 max:{maxRegisterAddress_RC}")

            
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
                if power_on[0] == b"RC" and response_pwr.get("response") == "rc_power_on":
                    print(response_pwr.get("result"))
                    
            except json.JSONDecodeError:
                self.poutput("Failed to decode the response.")






    #########################################################################
    # HV Commands #
    #########################################################################


    hv_set_init_conf = argparse.ArgumentParser()
    hv_set_init_conf.add_argument("port", type=str, help="The serial port used to communicate with the board")
    hv_set_init_conf.add_argument("channels", type=str, help="The channels intended to be configured")
    hv_set_init_conf.add_argument("voltage_set")
    hv_set_init_conf.add_argument("threshold_set")
    hv_set_init_conf.add_argument("limit_trip_time")
    hv_set_init_conf.add_argument("limit_voltage")
    hv_set_init_conf.add_argument("limit_current")
    hv_set_init_conf.add_argument("limit_temperature")
    hv_set_init_conf.add_argument("rate_up")
    hv_set_init_conf.add_argument("rate_down")

    @cmd2.with_argparser(hv_set_init_conf)
    @cmd2.with_category("HV")
    def do_set_init_conf(self, args: argparse.Namespace) -> None:
        "Function to set an initial configuration to the HV boards for the channel selected"

        if self._check_client("HV"):
            command_hv_init_conf = {

                "type" : "hv_command",
                "command" : "set_init_configuration",
                "port": args.port,
                "channel" : args.channels,
                "voltage_set" : args.voltage_set,
                "threshold_set" : args.threshold_set,
                "limit_trip_time" : args.limit_trip_time,
                "limit_voltage" : args.limit_voltage,
                "limit_current" : args.limit_current,
                "limit_temperature" : args.limit_temperature,
                "rate_up" : args.rate_up,
                "rate_down" : args.rate_down

            }

            control_socket.send_multipart([self.client.encode("utf-8"), json.dumps(command_hv_init_conf).encode("utf-8")])

            conf = control_socket.recv_multipart()

            try:
                response_conf = json.loads(conf[1].decode("utf-8"))
                if conf[0] == b"HV" and response_conf.get("response") == "hv_init_conf":
                    print(f"It was possible to set the initial configuration for the following channels: {response_conf.get('result')[0]}. \n It was not possible to set the following channels: {response_conf.get('result')[1]}")
                    
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
