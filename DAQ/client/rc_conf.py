import sys
import mmap

class RC:

    def __init__(self) -> None:

        self.maxRegisterAddress = 50
        self.maxChannels = 7

        try:
            self.fid = open('/dev/uio0', 'r+b', 0)
        except:
            print("E: UIO device /dev/uio0 not found")
            sys.exit(-1)
        

        try:
            self.regs = mmap.mmap(self.fid.fileno(), 0x10000)
        except Exception as e:
            print(f"E: Failed to map memory: {e}")
            self.fid.close()
            sys.exit(-1)

    def auto_int(self, x):
        if isinstance(x, int): 
            return x
        return int(x, 0)
    
    def checkRegBoundary(self, addr):
      if (addr < 0 or addr > self.maxRegisterAddress):
         return False
      return True
    
    def checkChannelsBoundary(self, channel):
        if (channel < 0 or channel > self.maxChannels):
            return False
        return True
    
    def read(self, addr):
        if (self.checkRegBoundary(self.auto_int(addr))):
            value = int.from_bytes(self.regs[self.auto_int(addr)*4:(self.auto_int(addr)*4)+4], byteorder='little')
            return (f'0x{value:08x}', value)
        else:
            return None

    
    def write(self, addr, value):
        if (self.checkRegBoundary(self.auto_int(addr))):

            try:
                self.regs[addr*4:(addr*4)+4] = int.to_bytes(value, 4, byteorder='little')
                return True
            except:
                print(f'E: write register error')
                return False

        else:
            print(f'E: register address outside boundary - min:0 max:{self.maxRegisterAddress}')
            return False
        
    def reset(self):
        """
        Reset function for the values of the register 0 and 1 of the Run Control
        """
        try:
            phase_1 = self.write(0, 0)
            if phase_1:
                self.write(1, 0)
                return True
            else:
                print("Something went wrong during the reset of the register 0")
                return False
        except Exception as e:
            print(f"Something went wrong during the reset of the register 0 and 1: {e}")
            return False
        
    
    def init_boot(self, value):
        """
        Write the same value to register 0 and 1 to open a specific channel in boot mode. One channel
        """
        try:
            reg_0 = self.write(0, value)
            if reg_0 == 0:
                self.write(1, value)
                return True
            else:
                print("Something went wrong during the initialisation of the register 0")
                return False
            
        except Exception as e:
            print(f"Something went wrong during the initialisation in boot mode of the channel: {e}")
            return False
        
    
    def init_data(self, channels):
        """
        Write the same value to register 0 and 1 to open a specific channel in data mode
        """
        try:
            if channels == "all":
                if self.write(1, 127):
                    self.write(0, 127)
                    print("All the channels has been opened in data mode")
                    return (True, channels)
                else:
                    print("Could not open all channels in data mode")
                    self.reset()
                    return (False,None)
            
            else:
                value = 0
                valid_channels = []
                channel_list = [int(x) for x in channels.split(",")]

                for channel in channel_list:
                    if self.checkChannelsBoundary(channel):
                        valid_channels.append(channel)
                        value += 2**(channel - 1)

                    else:
                        print(f"Channel {channel} is out of range. Ignored")
                        pass
                
                s = set(valid_channels)
                not_valid_channels = [x for x in channel_list if x not in s]
                
                if not valid_channels:
                    print("No valid channels provided. Aborting operation")
                    return (False, not_valid_channels)

                if self.write(1, value):
                    self.write(0, value)
                    print(f"The channels {channels} have been opened in data mode")
                    return (True, valid_channels)
                
                else:
                    print("Somethig went wrong opening the channels in data mode")
                    self.reset()
                    return (False, not_valid_channels)
                
        except Exception as e:
            print(f"During the initialisation of the Run Control something went wrong : {e}")
            return (False, None)
        

        
    def reg_monitoring(self, regs, channels):
        """Function to monitor the values of a general number of registers.
        """

        try:
            rc_list = [int(x) for x in regs.split(",")]
        except ValueError:
            print('E: failed to parse --reg - should be comma-separated list of integers')
            return None
        

        if channels == "all":
            channel_list = range(1, 8)
        else:
            try:
                channel_list = [int(x) for x in channels.split(",")]
            except ValueError:
                print("E: Failed to parse `channels` - it should be 'all' or a comma-separated list of integers.")
                return None


        channel_reg = {}


        for channel in channel_list:
            reg_value = {}
            for reg in rc_list:
                reg_value[reg] = self.read(reg)

            channel_reg[channel] = reg_value
        
        return channel_reg

        


