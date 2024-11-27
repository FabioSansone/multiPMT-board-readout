
import minimalmodbus
import time

class HV():

    def __init__(self) -> None:
        
        self.dev = None
        self.address = None
        self.maxAddress = 7

    def probe(self, serial, addr):
        dev = minimalmodbus.Instrument(serial, addr)
        dev.serial.baudrate = 115200
        dev.serial.timeout = 0.5
        dev.mode = minimalmodbus.MODE_RTU

        found = False
        for _ in range(0, 3):
            try:
                dev.read_register(0x00)  # read modbus address register
                found = True
                break
            except IOError:
                pass

        return found

    def open(self, serial, addr): #Serial corresponds to the port and addr to the channel
        if self.probe(serial, addr):
            self.dev = minimalmodbus.Instrument(serial, addr)
            self.dev.serial.baudrate = 115200
            self.dev.serial.timeout = 0.5
            self.dev.mode = minimalmodbus.MODE_RTU
            self.address = addr
            return True
        else:
            return False
        
    def checkAddressBoundary(self, channel):
        return channel >= 1 and channel <= 20
    
    def isConnected(self):
        return self.address is not None

    def getAddress(self):
        return self.address
    

    def getStatus(self):
        return self.dev.read_register(0x0006)

    def getVoltage(self):
        lsb = self.dev.read_register(0x002A)
        msb = self.dev.read_register(0x002B)
        value = (msb << 16) + lsb
        return value / 1000

    def getVoltageSet(self):
        return self.dev.read_register(0x0026)

    def setVoltageSet(self, value):
        self.dev.write_register(0x0026, value)

    def getCurrent(self):
        lsb = self.dev.read_register(0x0028)
        msb = self.dev.read_register(0x0029)
        value = (msb << 16) + lsb
        return value / 1000

    def getTemperature(self):
        return self.dev.read_register(0x0007)

    def getRate(self, fmt=str):
        rup = self.dev.read_register(0x0023)
        rdn = self.dev.read_register(0x0024)
        if fmt == str:
            return f'{rup}/{rdn}'
        else:
            return rup, rdn

    def setRateRampup(self, value):
        self.dev.write_register(0x0023, value, functioncode=6)

    def setRateRampdown(self, value):
        self.dev.write_register(0x0024, value)

    def getLimit(self, fmt=str):
        lv = self.dev.read_register(0x0027)
        li = self.dev.read_register(0x0025)
        lt = self.dev.read_register(0x002F)
        ltt = self.dev.read_register(0x0022)
        if fmt == str:
            return f'{lv}/{li}/{lt}/{ltt}'
        else:
            return lv, li, lt, ltt

    def setLimitVoltage(self, value):
        self.dev.write_register(0x0027, value)

    def setLimitCurrent(self, value):
        self.dev.write_register(0x0025, value)

    def setLimitTemperature(self, value):
        self.dev.write_register(0x002F, value)

    def setLimitTriptime(self, value):
        self.dev.write_register(0x0022, value)

    def setThreshold(self, value):
        self.dev.write_register(0x002D, value)

    def getThreshold(self):
        return self.dev.read_register(0x002D)

    def getAlarm(self):
        return self.dev.read_register(0x002E)

    def getVref(self):
        return self.dev.read_register(0x002C) / 10

    def powerOn(self):
        self.dev.write_bit(1, True)

    def powerOff(self):
        self.dev.write_bit(1, False)

    def reset(self):
        self.dev.write_bit(2, True)

    def getInfo(self):
        fwver = self.dev.read_string(0x0002, 1)
        pmtsn = self.dev.read_string(0x0008, 6)
        hvsn = self.dev.read_string(0x000E, 6)
        febsn = self.dev.read_string(0x0014, 6)
        dev_id = self.dev.read_registers(0x004, 2)
        return fwver, pmtsn, hvsn, febsn, (dev_id[1] << 16) + dev_id[0]

    def readMonRegisters(self):
        monData = {}
        baseAddress = 0x0000
        regs = self.dev.read_registers(baseAddress, 48)
        monData['status'] = regs[0x0006]
        monData['Vset'] = regs[0x0026]
        monData['V'] = ((regs[0x002B] << 16) + regs[0x002A]) / 1000
        monData['I'] = ((regs[0x0029] << 16) + regs[0x0028]) / 1000
        monData['T'] = self.convert_temp(regs[0x0007])
        monData['rateUP'] = regs[0x0023]
        monData['rateDN'] = regs[0x0024]
        monData['limitV'] = regs[0x0027]
        monData['limitI'] = regs[0x0025]
        monData['limitT'] = regs[0x002F]
        monData['limitTRIP'] = regs[0x0022]
        monData['threshold'] = regs[0x002D]
        monData['alarm'] = regs[0x002E]
        return monData
    

    def check_address(self, port, channel):
        if self.open(port, channel):
            if self.getAddress() == channel and self.isConnected() : #Address and channel as variables go from 1 to 7
                return True
            else:
                print("The HV board selected doesn't match the channel interested")
                return False
        else:
            return False
    
    def statusString(self, statusCode):
        statuses = {0: 'UP', 1: 'DOWN', 2: 'RUP', 3: 'RDN', 4: 'TUP', 5: 'TDN', 6: 'TRIP'}
        return statuses.get(statusCode, 'undef')
    


    def configure_channel(self, channel, port, voltage_set=None, threshold_set=None, limit_trip_time=None, limit_voltage=None, limit_current=None, limit_temperature=None, rate_up=None, rate_down=None):

        """Function to configure the signle channels with the given parameters"""

        if not self.open(port, channel):
            print(f"It was not possible to open channel: {channel}")
            return False
        
        time.sleep(0.2)
         
        if voltage_set is not None:
            self.setVoltageSet(voltage_set)
            time.sleep(0.2)
        if threshold_set is not None:
            self.setThreshold(threshold_set)
            time.sleep(0.2)
        if limit_trip_time is not None:
            self.setLimitTriptime(limit_trip_time)
            time.sleep(0.2)
        if limit_voltage is not None:
            self.setLimitVoltage(limit_voltage)
            time.sleep(0.2)
        if limit_current is not None:
            self.setLimitCurrent(limit_current)
            time.sleep(0.2)
        if limit_temperature is not None:
            self.setLimitTemperature(limit_temperature)
            time.sleep(0.2)
        if rate_up is not None:
            self.setRateRampup(rate_up)
            time.sleep(0.2)
        if rate_down is not None:
            self.setRateRampdown(rate_down)
            time.sleep(0.2)

        return True



    def process_channels(self, channels, port, **kwargs):

        """Process a list of channels or all of them"""

        valid_channels = []
        not_valid_channels = []

        if channels == "all":
            channel_list = range(1, 8)
        else:
            try:
                channel_list = [int(x) for x in channels.split(",")]
            except ValueError:
                print("Invalid channel format. Must be 'all' or comma-separated numbers.")
                return valid_channels, not_valid_channels #They are returned empty in this situation

        
        for channel in channel_list:

            time.sleep(0.1)
            if not self.checkAddressBoundary(channel):
                print(f"Channel {channel} is out of range. Ignored.")
                not_valid_channels.append(channel)
                continue
            
            time.sleep(0.1)
            if not self.check_address(port, channel):
                print("Channel and address selected don't match.")
                not_valid_channels.append(channel)
                continue
            
            time.sleep(0.1)
            if self.configure_channel(channel, port, **kwargs):
                valid_channels.append(channel)
                time.sleep(0.2)
                
            else:
                not_valid_channels.append(channel)
                time.sleep(0.2)

        return valid_channels, not_valid_channels
    

    def set_hv_init_configuration(self, port, channels, voltage_set, threshold_set, limit_trip_time, limit_voltage, limit_current, limit_temperature, rate_up, rate_down):

        """Function to set an initial configuration to the HV board."""

        return self.process_channels(
            channels, port,
            voltage_set=voltage_set,
            threshold_set=threshold_set,
            limit_trip_time=limit_trip_time,
            limit_voltage=limit_voltage,
            limit_current=limit_current,
            limit_temperature=limit_temperature,
            rate_up=rate_up,
            rate_down=rate_down
        )

    def set_voltage(self, channels, voltage_set, port):

        """Function to set only the voltage set to a single or multiple channels"""

        return self.process_channels(channels, port, voltage_set)
    

    
    def set_threshold(self, channels, threshold_set, port):

        """Function to set only the voltage set to a single or multiple channels"""

        return self.process_channels(channels, port, threshold_set)
    


    
    def set_limitI(self, channels, limit_current, port):

        """Function to set only the voltage set to a single or multiple channels"""

        return self.process_channels(channels, port, limit_current)
    

    
    def set_limitV(self, channels, limit_voltage, port):

        """Function to set only the voltage set to a single or multiple channels"""

        return self.process_channels(channels, port, limit_voltage)
    

    
    def set_limitTrip(self, channels, limit_trip_time, port):

        """Function to set only the voltage set to a single or multiple channels"""

        return self.process_channels(channels, port, limit_trip_time)
    




            
        