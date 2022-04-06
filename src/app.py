import sys
import argparse
import glob
import serial
from io import StringIO
from time import sleep
from intelhex import IntelHex

def _get_value(self, action, arg_string):
    type_func = self._registry_get('type', action.type, action.type)
    if not _callable(type_func):
        msg = _('%r is not callable')
        raise ArgumentError(action, msg % type_func)

    # convert the value to the appropriate type
    try:
        result = type_func(arg_string)

    # ArgumentTypeErrors indicate errors
    except ArgumentTypeError:
        name = getattr(action.type, '__name__', repr(action.type))
        msg = str(_sys.exc_info()[1])
        raise ArgumentError(action, msg)

    # TypeErrors or ValueErrors also indicate errors
    except (TypeError, ValueError):
        name = getattr(action.type, '__name__', repr(action.type))
        msg = _('invalid %s value: %r')
        raise ArgumentError(action, msg % (name, arg_string))

    # return the converted value
    return result

class FCDevUty:
    port = None
    fail_safe_max = 3
    verbose = True
    paths = []
    mode = ""
    read_size = 0x2000
    port_name = ""
    bank_num = 0
    manual_reset = False


    def serial_ports(self):
        """ Lists serial port names
    
            :raises EnvironmentError:
                On unsupported or unknown platforms
            :returns:
                A list of the serial ports available on the system
        """
        if sys.platform.startswith('win'):
            ports = ['COM%s' % (i + 1) for i in range(16)]
        elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
            # this excludes your current terminal "/dev/tty"
            ports = glob.glob('/dev/tty[A-Za-z]*')
        elif sys.platform.startswith('darwin'):
            ports = glob.glob('/dev/tty.*')
        else:
            raise EnvironmentError('Unsupported platform')
    
        result = []
        for port in ports:
            try:
                s = serial.Serial(port)
                s.close()
                result.append(port)
            except (OSError, serial.SerialException):
                pass
        return result

    def get_FCDEV_Port(self):
        ports = self.serial_ports()

        self.fail_safe_max = 3

        # search FCDEV
        for port_name in ports:
            self.port = serial.Serial(port=port_name,parity=serial.PARITY_NONE,bytesize=serial.EIGHTBITS,stopbits=serial.STOPBITS_ONE,timeout=0.5,writeTimeout=1,xonxoff=0,rtscts=0,dsrdtr=0,baudrate=9600)
            if not self.port.isOpen():
                continue

            if self.verbose:
                print("Check " + port_name)

            self.writePort("info")
            if self.waitString("FCDEV"):
                self.port.close()
                if self.verbose:
                    print(" Found!")
                return port_name
            self.port.close()
        return None

    def waitLf(self):
        while True:
            tmp = self.port.read(1)
            # print(tmp)
            if tmp == b'\n':
                break

    def waitString(self, *args):
        fail_safe = 0
        while True:
            tmp = self.port.readline().decode('ascii').rstrip('\r\n')
            if self.verbose:
                print(tmp)
            for check in args:
                if tmp.find(check) >= 0:
                    return True
            fail_safe = fail_safe + 1
            if fail_safe > self.fail_safe_max:
                return False

    def writePort(self, cmd):
        if self.verbose:
            print(cmd)
        try:
            self.port.write((cmd + "\r\n").encode())
        except serial.serialutil.SerialTimeoutException:
            return

    def resetPic(self):
        # Ctrl+C
        self.port.write(b"\x03")
        self.waitLf()

        # Init
        self.writePort("init")
        self.waitString("PIC")

        # Echo off
        self.writePort("ne")
        self.waitString("Echo")

    def changeRamBank(self, bank):
        print(" > Bank " + str(bank))
        self.writePort("b " + str(bank << 2))
        self.waitString("PIC", "FC->")

    def sendBinary(self, bin, addr):
        ih = IntelHex()
        for bt in bin:
            ih[addr] = bt
            addr = addr + 1

        sio = StringIO()
        ih.write_hex_file(sio, write_start_addr=True)
        hexstr = sio.getvalue()
        hexlines = hexstr.splitlines()
        for hex in hexlines:
            self.writePort(hex)
            if hex[1] != '0' or hex[2] != '0':
                print("\r   addr " + hex[3:7], end="")
            self.waitString("OK.", "Segment");
            #sleep(0.01)
        sio.close()
        print("")


    def sendNesPrg(self, fpath, manual_reset = True):
        print(" Load nes file : " + fpath)

        with open(fpath, mode='rb') as f:
            # skip nes header
            header = f.read(4)
            if header[0] != 0x4e or header[1] != 0x45 or header[2] != 0x53 or header[3] != 0x1a:
                print("not nes file")
                return True

            prg_bank = f.read(1)[0]
            chr_bank = f.read(1)[0]

            print(" PRG bank count:" + str(prg_bank))
            print(" CHR bank count:" + str(chr_bank))

            flag = f.read(1)[0] | (f.read(1)[0] << 8)
            # print(flag)

            f.read(8)

            prg_data = f.read(16384 * prg_bank)

            # setting mirror
            if flag & 1:
                print(" NameTable: Mirror-V")
                self.writePort("mv")
                self.waitString("PIC", "FC->")
            else:
                print(" NameTable: Mirror-H")
                self.writePort("mh")
                self.waitString("PIC", "FC->")

            if chr_bank > 0:
                print(" >> Write CHR");
                self.waitString("PIC")

            for bank in range(chr_bank):
                print(" > bank " + str(bank) )
                data = f.read(8192)
                self.sendChr(data, bank, 0x6000, manual_reset)

            self.writePort("reset")
            self.waitString("PIC", "FC->")

            self.writePort("we")
            self.waitString("Write")

            print(" >> Write PRG");
            if prg_bank == 2:
                self.sendBinary(prg_data, 0x8000)
            elif prg_bank == 1:
                self.sendBinary(prg_data, 0x8000)
                self.sendBinary(prg_data, 0xc000)

        self.writePort("wp")
        self.waitString("Write")

        print("Done.")
        return False

    def writeProtect(self, flag):
        if flag:
            print(" > Write Protect On")
            self.writePort("wp")
            self.waitString("Write")
        else:
            print(" > Write Protect Off")
            self.writePort("we")
            self.waitString("Write")

    def sendChr(self, data, bank, addr,manual_reset = True):
        self.writePort("uty")
        self.waitString("Uty-app installed")
        self.writePort("b " + str(bank))
        self.waitString("PIC", "FC->")
        self.writePort("mon")
        self.waitString("FC->")

        if manual_reset:
            input(" !! リセットボタンを押してからリターンを押してください")
            self.writePort("pr")
            self.waitString("FCdata: 00")
        else:
            self.waitString("PIC", "FC->")

        self.sendBinary(data, addr)

        self.writePort("w 0000 00 60 20")
        self.waitString("PIC", "FC->")
        self.writePort("g fe00")
        self.waitString("Running...")

        # port.write(b"\x03")	# Ctrl+C
        # writePort("")		# CRLF
        self.waitString("FC->")

        self.writePort("w 2000 0")
        self.waitString("FC->")

    def receiveBinary(self, path, addr, len):
        cmd = "i " + format(addr, 'x') + " " + format(len, 'x')
        self.writePort(cmd)
        reading_hex = False

        data = ''
        while self.port.readable():
            line = self.port.readline().decode('ascii')
            if not reading_hex and line.find(':') >= 0:
                print("\r   addr " + line[3:7], end="")
                # 読み込み開始
                reading_hex = True
                data += line
            elif line.find(':') == 0:
                print("\r   addr " + line[3:7], end="")
                data += line
            elif reading_hex and line.find(':') < 0:
                break;

        print("\n Write to file : " + path)
        f = StringIO(data)
        ih = IntelHex(f)
        f.close()
        with open(path, mode='wb') as wf:
            wf.write(ih.tobinarray())
        print("Done.")

    def __init__(self, paths, mode, addr, read_size, port_name, bank_num, manual_reset, verbose):
        self.paths = paths
        self.mode = mode
        self.addr = addr
        self.read_size = read_size
        self.port_name = port_name
        self.bank_num = bank_num
        self.manual_reset = manual_reset
        self.verbose = verbose
    
    def exec(self):
        if self.paths == None or len(self.paths) == 0:
            return True

        if self.port_name == None:
            self.port_name = self.get_FCDEV_Port()

        if self.port_name == None:
            print("Could not found FCDEV")
            return False

        self.fail_safe_max = 100
        self.port = serial.Serial(port=self.port_name,parity=serial.PARITY_NONE,bytesize=serial.EIGHTBITS,stopbits=serial.STOPBITS_ONE,timeout=3,xonxoff=0,rtscts=0,dsrdtr=0,baudrate=9600)

        print("=== Initialize FCDEV ===");
        self.resetPic()
        print("Done.\n")

        if self.mode == 'nes':
            print("=== Write NES file ===");
            if self.sendNesPrg(self.paths[0], self.manual_reset):
                return False

            if self.manual_reset:
                input(" !! リセットボタンを押しながらリターンを押し、リセットボタンを離してください")

            self.writePort("start")
            self.waitString("FC->")
        elif self.mode == 'chr':
            print("=== Write CHR ===");
            bank_num = self.bank_num
            self.writePort("mh")
            self.waitString("PIC", "FC->")
            data = bytearray()
            for path in self.paths:
                with open(path, mode='rb') as f:
                    data += f.read()

            v = memoryview(data)
            for ofs in range(0, len(v), 8192):
                self.sendChr(v[ofs:ofs + 8192], bank_num, 0x6000, self.manual_reset)
                bank_num = bank_num + 1
                if bank_num >= 4:
                    break
        elif self.mode == 'bin':
            bank_num = self.bank_num
            data = bytearray()
            for path in self.paths:
                with open(path, mode='rb') as f:
                    data += f.read()

            if self.addr < 0x8000:
                print("=== Write EX RAM ===");
                print(" Write to " + hex(self.addr))
                # EX RAM
                self.writeProtect(False)
                v = memoryview(data)
                read_size = 0x8000 - self.addr
                ofs = 0
                while ofs < len(v):
                    self.changeRamBank(bank_num)
                    ofs_tail = ofs + read_size
                    if ofs_tail > len(v):
                        ofs_tail = len(v)
                    self.sendBinary(v[ofs:ofs_tail], self.addr)
                    self.addr += read_size
                    if self.addr >= 0x8000:
                        self.addr = self.addr - 0x2000
                    ofs = ofs + read_size
                    read_size = 8192
                    bank_num = bank_num + 1
                    if bank_num >= 4:
                        break
                self.writeProtect(True)
            else:
                # PRG ROM
                print("=== Write PRG ROM ===");
                print(" Write to " + hex(self.addr))
                self.writeProtect(False)
                self.sendBinary(data, self.addr)
                self.writeProtect(True)
        elif self.mode == 'read':
            print("=== Read from ROM ===");
            print(" Read from " + hex(self.addr) + " length:" + hex(self.read_size))
            self.receiveBinary(self.paths[0], self.addr, self.read_size)

        return False
    

def _auto_int(x):
    return int(x, 0)

def main():
    parser = argparse.ArgumentParser(description='FCDEV transfer utility Version 0.1.0 Copyright 2022 H.O SOFT Inc.')

    parser.add_argument('-r', '--reset', help='manual reset mode', action='store_true')
    parser.add_argument('-m', '--mode', choices=['nes','chr','bin','read'], help='transfer mode (default = nes)', default='nes')
    parser.add_argument('-a', '--addr', help='transfer address (default = 0x6000)', type=_auto_int, default=0x6000)
    parser.add_argument('-s', '--size', help='read size (default = 0x2000)', type=_auto_int, default=0x2000)
    parser.add_argument('-p', '--port', help='serial port name (auto search if not present)', type=str, default=None)
    parser.add_argument('-b', '--bank', help='bank number (default = 0)', type=int, default=0)
    parser.add_argument('-v', '--verbose', help='verbose mode', action='store_true')
    parser.add_argument('path', help='file path(s)', nargs="*")

    args = parser.parse_args()

    paths = args.path
    mode = args.mode
    addr = args.addr
    read_size = args.size
    port_name = args.port
    bank_num = args.bank
    manual_reset = args.reset
    verbose = args.verbose

    fcdevuty = FCDevUty(paths, mode, addr, read_size, port_name, bank_num, manual_reset, verbose)
    if fcdevuty.exec():
        parser.print_help()
        exit()

if __name__=='__main__':
    main()
