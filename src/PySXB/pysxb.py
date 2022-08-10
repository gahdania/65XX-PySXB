"""PySXB:  Basic python implementation of Terbium IDE, (TIDE).

Based on the work of Chris Baird <cjb@brushtail.apana.org.au> July 2019

David Couples
2021 November
"""

import serial

AT = (0x55, 0xAA)
# ???  = 0x01
WRITE = 0x02
READ = 0x03
TIDE = 0x04
EXEC = 0x05
BLK_SIZE = 62
OK = 0xCC


class PySXB(serial.Serial):
    """

    Args:
        port (str): the device path for the serial port of the SXB board
        speed (int): speed of communication (baud rate) default 9600
        emulation_mode (bool): Sets the if emulation is turned on or off
            defaults to True.  W65C02SXB also should be true
        *args: additional positional args to pass onto parent class
        **kwargs: additional keyword args to pass onto parent class
    """

    def __init__(self, port, emulation_mode=True, *args, **kwargs):
        super().__init__(port, 9600, *args, **kwargs)

        # load TIDE data from the board
        if self._command(TIDE):
            tide_data = bytearray(self.read(0x20))
            self.mon_ram = self.decode(tide_data[:3])
            self.cpu_type = tide_data[3]
            self.board_id = tide_data[4]
            self.mon_rom = self.decode(tide_data[8:11])
            self.shadow_vector_base = self.decode(tide_data[11:14])
            self.hw_io = self.decode(tide_data[14:17])
            self.hw_vector_base = self.decode(tide_data[17:20])

            if not self.cpu_type:
                self.emulation = True

            if self.cpu_type:
                self.emulation = emulation_mode

    @staticmethod
    def decode(byte_array):
        return_val = 0
        for i, byte in enumerate(byte_array):
            return_val |= byte << i * 8

        return return_val

    @staticmethod
    def encode(number, address=True):
        if address:
            return (number & 255), ((number >> 8) & 255), ((number >> 16) & 255)
        
        return (number & 255), ((number >> 8) & 255)

    def hex(self, data, start_address=None):
        line = ""

        if not start_address:
            start_address = 0

        if isinstance(data, int):
            data = self.encode(data, False)

        for i, datum in enumerate(data):

            if i == 0:
                line = f"{start_address:#06x}:"
            if i > 0 and i % 16 == 0:
                line += f"\n{i+start_address:#06x}:"
            if (i % 8 == 0) and (i % 16 != 0):
                line += " "
            line += f" {datum:02X}"

        return line

    @property
    def stack(self):
        return self.read_board(0x100, 256)

    @property
    def processor(self):
        return self.read_board(self.mon_ram, 16)

    @property
    def zero_page(self):
        return self.read_board(0x00, 256)

    @property
    def irq_vector(self):
        address = self.shadow_vector_base + 10

        if self.emulation:
            return address + 16

        return address

    @property
    def reset_vector(self):
        address = self.shadow_vector_base + 8

        if self.emulation:
            return address + 16

        return address

    @property
    def nmi_vector(self):
        address = self.shadow_vector_base + 6

        if self.emulation:
            return address + 16

    @property
    def break_vector(self):
        address = self.shadow_vector_base + 2

        if self.emulation:
            return address + 24

        return address

    @property
    def abort_vector(self):
        address = self.shadow_vector_base + 4

        if not self.cpu_type:
            return None

        if self.emulation:
            return address + 16

        return address

    @property
    def coprocessor_vector(self):
        address = self.shadow_vector_base

        if not self.cpu_type:
            return None

        if self.emulation:
            return address + 16

        return address

    def hardware_address(self, address):
        return self.hw_vector_base & 0xff00 | address & 0x00ff

    def _at(self):
        if self.write(AT):
            try:
                return ord(self.read(1)) == OK
            except ValueError:
                return False

    def _command(self, cmd_code, *, address=None, length=None):

        if not self._at():
            return None

        command = bytearray((cmd_code,))

        if address:
            for element in self.encode(address):
                command.append(element)

        if length:
            for element in self.encode(length, False):
                command.append(element)

        try:
            return self.write(command) > 0
        except serial.SerialTimeoutException as error:
            print(f"Error: {error}\n")
            return None
        except TypeError as error:
            print(f"Error: {error}\n")
            return None

    def write_board(self, address, data):
        length = len(data)

        if self._command(WRITE, address=address, length=length):
            if length < BLK_SIZE:
                return self.write(data)

            for blk in range(0, length, BLK_SIZE):
                if blk + BLK_SIZE < length:
                    self.write(data[blk:blk+BLK_SIZE])
                    continue
                self.write(data[blk:length])

        return 0

    def execute(self, address, a_reg=0, x_reg=0, y_reg=0, processor_flags=0x76):
        """
        """
        a_reg = self.encode(a_reg, False)
        x_reg = self.encode(x_reg, False)
        y_reg = self.encode(y_reg, False)

        address = self.encode(address)
        processor_state = (
            a_reg,                      # A Register
            x_reg,                      # X register
            y_reg,                      # Y register
            address[0], address[1],     # Program Counter
            0, 0,                       # Direct Register
            255, 1,                     # Stack Pointer
            processor_flags,            # Processor status flags
            self.emulation,             # Emulation Off/On
            0,                          # Program Bank Register
            0                           # Data Bank Register
        )

        self.write_board(self.mon_ram, processor_state)
        return self._command(EXEC, length=1)

    def read_board(self, address, length):

        self._command(READ, address=address, length=length)
        if length < BLK_SIZE:
            return self.read(length)

        temp = bytearray(length)
        for blk in range(0, length, BLK_SIZE):
            if blk + BLK_SIZE < length:
                temp[blk: blk + BLK_SIZE] = self.read(BLK_SIZE)
                continue
            temp[blk:length] = self.read(length-blk)
        return temp

    def load(self, file):
        with open(file, 'rb') as fh:
            rom_data = fh.read()

        if rom_data[0] == 0x5a:     # checking for SXB flag symbol from the WDC assembler/Compiler

            code_address = self.decode(rom_data[1:4])
            code_length = self.decode(rom_data[4:6])
            code = rom_data[7:7+code_length]
            self.write_board(code_address, code)
            return code_address, code_length

        raise ValueError("Program needs to be compiled/assembled with the -g option")
