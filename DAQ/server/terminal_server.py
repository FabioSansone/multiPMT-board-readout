import cmd2
import argparse
import zmq
import json
import time

dict_client_port = {

    "RC" : "8005",
    "HV" : "8006"

}


context = zmq.Context()

maxRegisterAddress_RC = 50


class ServerTerminal(cmd2.Cmd):

    "A terminal application to switch and interact with the clients on the MainBoard"

    intro  = "Welcome to the control interface of the multiPMT. Type ? or help to list commands."
    prompt = "|Main>"
    client = None
    client_socket = None

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

        if args.client not in client_list:
            self.poutput(f"Invalid client name. Available clients: {client_list}")
            return

        if self.client_socket is not None:
            self.client_socket.close()

        self.client_socket = context.socket(zmq.ROUTER)
        #self.client_socket.setsockopt(zmq.RCVTIMEO, 6000)

        try:
            port = dict_client_port.get(args.client)
            self.client_socket.bind(f"tcp://*:{port}")
        except zmq.ZMQError as e:
            self.poutput(f"Failed to bind socket on port {port}: {e}")
            return
        
        self.poutput(f"Waiting for connection with client {args.client} on port {port}...")


        client_id = args.client.encode("utf-8")
        connected = False
        start_time = time.time()

    
        while not connected and (time.time() - start_time < timeout):
            try:
                client_id_received, information = self.client_socket.recv_multipart()

                if client_id_received == client_id and information == b"Ping":
                    self.poutput("Ping signal received")
                    self.client_socket.send_multipart([client_id, b"Alive"])

                    response = self.client_socket.recv_multipart()
                    if response[0] == client_id and response[1] == b"Connection successful":
                        self.poutput(f"Connection was successful with client: {args.client}")
                        self.client = args.client
                        self.prompt = f"|{args.client}>"
                        connected = True
                else:
                    self.poutput("Received unexpected message or mismatched client ID.")

            except zmq.Again:
                continue


        
        if not connected:
            self.poutput(f"Failed to connect with client {args.client} within {timeout} seconds.")
            self.client_socket.close()
            self.client_socket = None



    def _check_client(self, required_client):
        """
        Utility method to ensure the command is used in the correct client page.
        """
        if self.client != required_client:
            self.poutput(f"This command is only available in the {required_client} client page.")
            return False
        return True
    

    
    @cmd2.with_category("Clients Selection")
    def do_back(self, _) -> None:
        """
        Return to the main menu.
        """
        if self.client_socket is None:
            self.poutput("No client is connected.")
            return

        command_back = {
            "type": "clients",
            "command": "back"
        }

        try:
            self.client_socket.send_multipart([self.client.encode("utf-8"), json.dumps(command_back).encode("utf-8")])
            self.poutput(f"Returning to the main menu from client {self.client}.")
        except zmq.ZMQError as e:
            self.poutput(f"Failed to send 'back' command: {e}")

        self.client = None
        self.prompt = "|Main>"




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


            self.client_socket.send_multipart([self.client.encode("utf-8"), json.dumps(command_back).encode("utf-8")])
            
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

            self.client_socket.send_multipart([self.client.encode("utf-8"), json.dumps(command_rc_read).encode("utf-8")])
        
            read = self.client_socket.recv_multipart()

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


            self.client_socket.send_multipart([self.client.encode("utf-8"), json.dumps(command_rc_write).encode("utf-8")])
        
            write = self.client_socket.recv_multipart()

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

            self.client_socket.send_multipart([self.client.encode("utf-8"), json.dumps(command_rc_pwr_on).encode("utf-8")])

            power_on = self.client_socket.recv_multipart()

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
    hv_set_init_conf.add_argument("channels", type=str, help="The channels intended to be configured")
    hv_set_init_conf.add_argument("--port", type=str, default="/dev/ttyPS1", help="The serial port used to communicate with the board")
    hv_set_init_conf.add_argument("--voltage_set", type=int, default=800, help="The default voltage to set (default: 800)")
    hv_set_init_conf.add_argument("--threshold_set", type=int, default=100, help="The threshold to set (default: 100)")
    hv_set_init_conf.add_argument("--limit_trip_time", type=int, default=2, help="The trip time limit (default: 2)")
    hv_set_init_conf.add_argument("--limit_voltage", type=int, default=100, help="The voltage limit (default: 100)")
    hv_set_init_conf.add_argument("--limit_current", type=int, default=5, help="The current limit (default: 5)")
    hv_set_init_conf.add_argument("--limit_temperature", type=int, default=50, help="The temperature limit (default: 50)")
    hv_set_init_conf.add_argument("--rate_up", type=int, default=25, help="The rate of voltage increase (default: 25)")
    hv_set_init_conf.add_argument("--rate_down", type=int, default=25, help="The rate of voltage decrease (default: 25)")

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

            self.client_socket.send_multipart([self.client.encode("utf-8"), json.dumps(command_hv_init_conf).encode("utf-8")])

            conf = self.client_socket.recv_multipart()

            try:
                response_conf = json.loads(conf[1].decode("utf-8"))
                if conf[0] == b"HV" and response_conf.get("response") == "hv_init_conf":
                    self.poutput(f"It was possible to set the initial configuration for the following channels: {response_conf.get('result')[0]}. \n It was not possible to set the following channels: {response_conf.get('result')[1]}")
                    
            except json.JSONDecodeError:
                self.poutput("Failed to decode the response.")

    
    hv_set_voltage_set = argparse.ArgumentParser()
    hv_set_voltage_set.add_argument("channels", type=str, help="The channels intended to be configured")
    hv_set_voltage_set.add_argument("voltage_set", type=int, help="The voltage to set")
    hv_set_voltage_set.add_argument("--port", type=str, default="/dev/ttyPS1", help="The serial port used to communicate with the board")


    @cmd2.with_argparser(hv_set_voltage_set)
    @cmd2.with_category("HV")
    def do_set_voltage(self, args: argparse.Namespace) -> None:
        "Function to set the voltage set to the HV boards for the channels selected"


        if self._check_client("HV"):
            command_hv_set_voltage = {

                "type" : "hv_command",
                "command" : "set_voltage",
                "port": args.port,
                "channel" : args.channels,
                "voltage_set" : args.voltage_set
            }

            self.client_socket.send_multipart([self.client.encode("utf-8"), json.dumps(command_hv_set_voltage).encode("utf-8")])

            voltage_set = self.client_socket.recv_multipart()

            try:
                response_volt = json.loads(voltage_set[1].decode("utf-8"))
                if voltage_set[0] == b"HV" and response_volt.get("response") == "hv_voltage_set":
                    self.poutput(f"It was possible to set the voltage for the following channels: {response_volt.get('result')[0]}. \n It was not possible to set the voltage for the following channels: {response_volt.get('result')[1]}")
                    
            except json.JSONDecodeError:
                self.poutput("Failed to decode the response.")
    

    hv_threshold_set = argparse.ArgumentParser()
    hv_threshold_set.add_argument("channels", type=str, help="The channels intended to be configured")
    hv_threshold_set.add_argument("threshold_set", type=int, help="The threshold to set")
    hv_threshold_set.add_argument("--port", type=str, default="/dev/ttyPS1", help="The serial port used to communicate with the board")


    @cmd2.with_argparser(hv_threshold_set)
    @cmd2.with_category("HV")
    def do_set_threshold(self, args: argparse.Namespace) -> None:
        "Function to set the threshold set to the HV boards for the channels selected"


        if self._check_client("HV"):
            command_hv_set_threshold = {

                "type" : "hv_command",
                "command" : "set_threshold",
                "port": args.port,
                "channel" : args.channels,
                "threshold" : args.threshold_set
            }

            self.client_socket.send_multipart([self.client.encode("utf-8"), json.dumps(command_hv_set_threshold).encode("utf-8")])

            threshold_set = self.client_socket.recv_multipart()

            try:
                response_threshold = json.loads(threshold_set[1].decode("utf-8"))
                if threshold_set[0] == b"HV" and threshold_set.get("response") == "hv_threshold":
                    self.poutput(f"It was possible to set the threshold for the following channels: {response_threshold.get('result')[0]}. \n It was not possible to set the voltage for the following channels: {response_threshold.get('result')[1]}")
                    
            except json.JSONDecodeError:
                self.poutput("Failed to decode the response.")

    



    hv_limitV = argparse.ArgumentParser()
    hv_limitV.add_argument("channels", type=str, help="The channels intended to be configured")
    hv_limitV.add_argument("limit_voltage", type=int, help="The voltage limit to set")
    hv_limitV.add_argument("--port", type=str, default="/dev/ttyPS1", help="The serial port used to communicate with the board")


    @cmd2.with_argparser(hv_limitV)
    @cmd2.with_category("HV")
    def do_set_limitV(self, args: argparse.Namespace) -> None:
        "Function to set the limit voltage to the HV boards for the channels selected"


        if self._check_client("HV"):
            command_hv_limitV = {

                "type" : "hv_command",
                "command" : "set_limitV",
                "port": args.port,
                "channel" : args.channels,
                "threshold" : args.limit_voltage
            }

            self.client_socket.send_multipart([self.client.encode("utf-8"), json.dumps(command_hv_limitV).encode("utf-8")])

            limitV = self.client_socket.recv_multipart()

            try:
                response_limitV = json.loads(limitV[1].decode("utf-8"))
                if limitV[0] == b"HV" and limitV.get("response") == "hv_voltage_limit":
                    self.poutput(f"It was possible to set the threshold for the following channels: {response_limitV.get('result')[0]}. \n It was not possible to set the voltage for the following channels: {response_limitV.get('result')[1]}")
                    
            except json.JSONDecodeError:
                self.poutput("Failed to decode the response.")


    



    hv_limitI = argparse.ArgumentParser()
    hv_limitI.add_argument("channels", type=str, help="The channels intended to be configured")
    hv_limitI.add_argument("limit_current", type=int, help="The current limit to set")
    hv_limitI.add_argument("--port", type=str, default="/dev/ttyPS1", help="The serial port used to communicate with the board")


    @cmd2.with_argparser(hv_limitI)
    @cmd2.with_category("HV")
    def do_set_limitI(self, args: argparse.Namespace) -> None:
        "Function to set the limit current to the HV boards for the channels selected"


        if self._check_client("HV"):
            command_hv_limitI = {

                "type" : "hv_command",
                "command" : "set_limitI",
                "port": args.port,
                "channel" : args.channels,
                "threshold" : args.limit_current
            }

            self.client_socket.send_multipart([self.client.encode("utf-8"), json.dumps(command_hv_limitI).encode("utf-8")])

            limitI = self.client_socket.recv_multipart()

            try:
                response_limitI = json.loads(limitI[1].decode("utf-8"))
                if limitI[0] == b"HV" and limitI.get("response") == "hv_current_limit":
                    self.poutput(f"It was possible to set the threshold for the following channels: {response_limitI.get('result')[0]}. \n It was not possible to set the voltage for the following channels: {response_limitI.get('result')[1]}")
                    
            except json.JSONDecodeError:
                self.poutput("Failed to decode the response.")


    



    hv_limitTrip = argparse.ArgumentParser()
    hv_limitTrip.add_argument("channels", type=str, help="The channels intended to be configured")
    hv_limitTrip.add_argument("limit_trip", type=int, help="The trip time limit to set")
    hv_limitTrip.add_argument("--port", type=str, default="/dev/ttyPS1", help="The serial port used to communicate with the board")


    @cmd2.with_argparser(hv_limitTrip)
    @cmd2.with_category("HV")
    def do_set_limitTrip(self, args: argparse.Namespace) -> None:
        "Function to set the trip time to the HV boards for the channels selected"


        if self._check_client("HV"):
            command_hv_limitTrip = {

                "type" : "hv_command",
                "command" : "set_limitTrip",
                "port": args.port,
                "channel" : args.channels,
                "threshold" : args.limit_trip
            }

            self.client_socket.send_multipart([self.client.encode("utf-8"), json.dumps(command_hv_limitTrip).encode("utf-8")])

            limitTrip = self.client_socket.recv_multipart()

            try:
                response_limitTrip = json.loads(limitTrip[1].decode("utf-8"))
                if limitTrip[0] == b"HV" and limitTrip.get("response") == "hv_triptime_limit":
                    self.poutput(f"It was possible to set the threshold for the following channels: {response_limitTrip.get('result')[0]}. \n It was not possible to set the voltage for the following channels: {response_limitTrip.get('result')[1]}")
                    
            except json.JSONDecodeError:
                self.poutput("Failed to decode the response.")







if __name__ == '__main__':

    app = ServerTerminal()

    try:
        app.cmdloop()
    except KeyboardInterrupt:
        print("\n Shutting down...")
    finally:
        if app.client_socket:
            app.client_socket.close()
            context.term()
