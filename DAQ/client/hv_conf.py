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
    

    def check_address(self, channel):
        if self.checkAddressBoundary(channel):
            print(self.getAddress())
            if self.getAddress() == channel  : #Address and channel as variables go from 1 to 7
                return True
            else:
                print("The HV board selected doesn't match the channel interested")
                return False
        else:
            print("The HV board is not connected and was not possible to retrieve and check its address")
            return False
    
    def statusString(self, statusCode):
        statuses = {0: 'UP', 1: 'DOWN', 2: 'RUP', 3: 'RDN', 4: 'TUP', 5: 'TDN', 6: 'TRIP'}
        return statuses.get(statusCode, 'undef')
    
    def set_hv_init_configuration(self, port, channels ,voltage_set = 800, threshold_set=100, limit_trip_time=2, limit_voltage=100, limit_current=5, limit_temperature=50, rate_up=25, rate_down=25):
        
        if channels == "all":
            all_valid_channels = []
            not_all_valid_channels = []
            try:
                for i in range(1, 8):
                    if self.open(port, i):
                        if self.statusString(self.getStatus()) == "DOWN":
                            self.setVoltageSet(voltage_set)
                            time.sleep(0.2)
                            self.setLimitVoltage(limit_voltage)
                            time.sleep(0.2)
                            self.setLimitCurrent(limit_current)
                            time.sleep(0.2)
                            self.setLimitTemperature(limit_temperature)
                            time.sleep(0.2)
                            self.setLimitTriptime(limit_trip_time)
                            time.sleep(0.2)
                            self.setThreshold(threshold_set)
                            time.sleep(0.2)
                            self.setRateRampup(rate_up)
                            time.sleep(0.2)
                            self.setRateRampdown(rate_down)
                            time.sleep(5)
                            
                        else:
                            self.powerOff()
                            time.sleep(5)
                            self.setVoltageSet(voltage_set)
                            time.sleep(0.2)
                            self.setLimitVoltage(limit_voltage)
                            time.sleep(0.2)
                            self.setLimitCurrent(limit_current)
                            time.sleep(0.2)
                            self.setLimitTemperature(limit_temperature)
                            time.sleep(0.2)
                            self.setLimitTriptime(limit_trip_time)
                            time.sleep(0.2)
                            self.setThreshold(threshold_set)
                            time.sleep(0.2)
                            self.setRateRampup(rate_up)
                            time.sleep(0.2)
                            self.setRateRampdown(rate_down)
                            time.sleep(5)
                            
                        all_valid_channels.append(channel)
                                            
                    else:
                        print(f"It was not possible to open channel: {channel}")
                        not_all_valid_channels.append(channel)
                        pass

            except Exception as e:
                print(f"It was not possible to configure the HV board as desired: {e}")
                return (False,None)
            
            return (all_valid_channels, not_all_valid_channels)
        
        else:
            valid_channels = []
            not_valid_channels = []
            channel_list = [int(x) for x in channels.split(",")]
            for channel in channel_list:
                if self.check_address(channel):
                    if self.open(port, channel) and self.isConnected():
                        if self.statusString(self.getStatus()) == "DOWN":
                            self.setVoltageSet(voltage_set)
                            time.sleep(0.2)
                            self.setLimitVoltage(limit_voltage)
                            time.sleep(0.2)
                            self.setLimitCurrent(limit_current)
                            time.sleep(0.2)
                            self.setLimitTemperature(limit_temperature)
                            time.sleep(0.2)
                            self.setLimitTriptime(limit_trip_time)
                            time.sleep(0.2)
                            self.setThreshold(threshold_set)
                            time.sleep(0.2)
                            self.setRateRampup(rate_up)
                            time.sleep(0.2)
                            self.setRateRampdown(rate_down)
                            time.sleep(5)
                        
                        else:
                            self.powerOff()
                            time.sleep(5)
                            self.setVoltageSet(voltage_set)
                            time.sleep(0.2)
                            self.setLimitVoltage(limit_voltage)
                            time.sleep(0.2)
                            self.setLimitCurrent(limit_current)
                            time.sleep(0.2)
                            self.setLimitTemperature(limit_temperature)
                            time.sleep(0.2)
                            self.setLimitTriptime(limit_trip_time)
                            time.sleep(0.2)
                            self.setThreshold(threshold_set)
                            time.sleep(0.2)
                            self.setRateRampup(rate_up)
                            time.sleep(0.2)
                            self.setRateRampdown(rate_down)
                            time.sleep(5)

                        valid_channels.append(channel)

                                        
                    else:
                        print(f"It was not possible to open channel: {channel}")
                        not_valid_channels.append(channel)
                        pass
                else:
                    print(f"Channel {channel} is out of range. Ignored")
                    not_valid_channels.append(channel)
                    pass

            return(valid_channels, not_valid_channels)

            
        