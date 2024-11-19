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
            self.perror(f'E: register address outside boundary - min:0 max:{self.maxRegisterAddress}')

    
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
                    return True
                else:
                    print("Could not open all channels in data mode")
                    self.reset()
                    return False
            
            else:
                value = 0
                for channel in channels:
                    if self.checkChannelsBoundary(channel):
                        value += 2**(channel - 1)

                    else:
                        print(f"Channel {channel} is out of range. Ignored")
                        pass

                if self.write(1, value):
                    self.write(0, value)
                    print(f"The channels {channels} have been opened in data mode")
                    return True
                
                else:
                    print("Somethig went wrong opening the channels in data mode")
                    self.reset()
                    return False
                
        except Exception as e:
            print(f"During the initialisation of the Run Control something went wrong : {e}")
            return False