import sys
import mmap

class RC:

    def __init__(self) -> None:

        self.maxRegisterAddress = 50

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
        return int(x, 0)
    
    def checkRegBoundary(self, addr):
      if (addr < 0 or addr > self.maxRegisterAddress):
         return False
      return True
    
    def read(self, addr):
        if (self.checkRegBoundary(self.auto_int(addr))):
            value = int.from_bytes(self.regs[self.auto_int(addr)*4:(self.auto_int(addr)*4)+4], byteorder='little')
            return (f'0x{value:08x}', value)
        else:
            self.perror(f'E: register address outside boundary - min:0 max:{self.maxRegisterAddress}')

