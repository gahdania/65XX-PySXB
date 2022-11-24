"""PySXB:  Basic python implementation of Terbium IDE, (TIDE).

Based on the work of Chris Baird <cjb@brushtail.apana.org.au> July 2019

David Couples
2021 November
"""
from __future__ import annotations

import serial

AT = bytes((0x55, 0xAA))
# ???  = 0x01
WRITE = 0x02
READ = 0x03
TIDE = 0x04
EXEC = 0x05
BLK_SIZE = 0x3E
OK = 0xCC


class PySXB(serial.Serial):
    """PySXB
    Allows basic access for Linux users for the Western Design Center SXB
    boards

    Args:
        port (str): the device path for the serial port of the SXB board
        speed (int): speed of communication (baud rate) default 9600
        emulation_mode (bool): Sets the if emulation is turned on or off
            defaults to True.  W65C02SXB should be true
        **kwargs: additional keyword args to pass for serial package
    """

    def __init__(self, port, baud=9600, emulation_mode=True, **kwargs):

        super().__init__(port=port, baudrate=baud, **kwargs)

        tide_data = bytearray(29)

        # load TIDE data from the board
        
        if self.sxb_command(TIDE):
            tide_data = self.read(29)

        if tide_data:
            self.mon_ram = self.decode(tide_data[:3])
            self.cpu_type = tide_data[3]
            self.board_id = tide_data[4]
            self.mon_rom = self.decode(tide_data[8:11])
            self.shadow_vector_base = self.decode(tide_data[11:14])
            self.hw_io = self.decode(tide_data[14:17])
            self.hw_vector_base = self.decode(tide_data[17:20])

            if self.cpu_type:
                self.emulation = emulation_mode

            if not self.cpu_type:
                self.emulation = True

    @staticmethod
    def decode(byte_array):
        """Decode the little endian addressing to int

        Args:
            byte_array (bytearray/int/bytes): the byte array of address or data length

        Returns:
            int: the decoded address or length
        """
        return_val = 0
        for i, byte in enumerate(byte_array):
            return_val |= byte << i * 8

        return return_val

    @staticmethod
    def encode(number, address=True):
        """Encode number into a two or three byte little endian byte array

        Args:
            number (int): the address or length to convert
            address (bool): if the number is an address(true) or length(false)

        Returns:
            bytearray: the little endian byte array
        """
        if address:
            return (number & 255), ((number >> 8) & 255), ((number >> 16) & 255)
        
        return (number & 255), ((number >> 8) & 255)

    def hex(self, data, start_address=None):
        """Used to print the hex output

        Args:
            data (bytearray): contains the data to display
            start_address (int): starting address for the output

        Returns:
            string: formatted output displaying the data
        """
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

        print(line)

    @property
    def stack(self):
        """Data contained within the stack region of memory (0x0100 - 0x01FF)

        Returns:
            bytearray: stack data
        """
        return self.sxb_read(0x0100, 0x0100)

    @property
    def processor(self):
        """Returns the processor status

        Returns:
            bytearray: processor status data
        """
        return self.sxb_read(0x10, self.mon_ram)

    @property
    def zero_page(self):
        """Returns the data contained within the Zero Page (0x0000 - 0x00FF)

        Returns:
            bytearray:  "zero page" (0x0000 - 0x00FF) data
        """
        return self.sxb_read(0x0100, 0x0000)

    @property
    def irq_vector(self):
        """Returns the address of the interrupt vector

        Returns:
            int: address of the IRQ vector
        """
        address = self.shadow_vector_base + 10

        if self.emulation:
            return address + 16

        return address

    @property
    def reset_vector(self):
        """Returns the address of the reset vector

        Returns:
            int: address of the reset vector
        """
        address = self.shadow_vector_base + 8

        if self.emulation:
            return address + 16

        return address

    @property
    def nmi_vector(self):
        """Returns the address of the non-maskable interrupt vector

        Returns:
            int: address of the NMI vector
        """
        address = self.shadow_vector_base + 6

        if self.emulation:
            return address + 16

    @property
    def break_vector(self):
        """Returns the address of the break interrupt vector

        Returns:
            int: address of the break IRQ vector
        """
        address = self.shadow_vector_base + 2

        if self.emulation:
            return address + 24

        return address

    @property
    def abort_vector(self):
        """Returns the address of the abort vector

        Returns:
            int: address of the abort vector
        """
        address = self.shadow_vector_base + 4

        if not self.cpu_type:
            return None

        if self.emulation:
            return address + 16

        return address

    @property
    def coprocessor_vector(self):
        """Returns the address of the coprocessor vector

        Returns:
            int: address of the coprocessor vector
        """
        address = self.shadow_vector_base

        if not self.cpu_type:
            return None

        if self.emulation:
            return address + 16

        return address

    def hardware_address(self, address):
        """Returns the base address of the ports for the SXB

        Returns:
            int: address of the base hardware address
        """
        return self.hw_vector_base & 0xff00 | address & 0x00ff

    def sxb_at(self):
        """AT - Used to check to see if the SXB is ready to accept commands

        Returns:
            bool: returns true if the SXB is ready, else false
        """
        try:
            if self.write(AT):
                return ord(self.read(1)) == OK
        except serial.SerialTimeoutException:
            return False

    def sxb_command(self, cmd_code, *, address=None, length=None):
        """submits a command to the board

        Args:
            cmd_code (int): the command code to issue
            address (int): address to begin the command if applicable
            length (int): the byte count for the command

        Returns:
            (bool): returns true if more than one byte was successfully written, else false
        """

        if self.sxb_at():
            command = bytearray((cmd_code,))
    
            if address:
                for element in self.encode(address):
                    command.append(element)
    
            if length:
                for element in self.encode(length, False):
                    command.append(element)
    
            try:
                write_count = self.write(command)
                return write_count > 0
            except serial.SerialTimeoutException as error:
                print(f"Error: {error}\n")
                return None
            except TypeError as error:
                print(f"Error: {error}\n")
                return None

    def sxb_write(self, data, address=None):
        """writes the data to the board

        Args:
            data (tuple/list): the data to be written
            address (int): the starting address

        Returns:
            int: bytes written to port
        """

        if not address:
            return self.write(data)

        length = len(data)

        if self.sxb_command(WRITE, address=address, length=length):
            if length < BLK_SIZE:
                return self.write(data)

            for blk in range(0, length, BLK_SIZE):
                if blk + BLK_SIZE < length:
                    self.write(data[blk:blk+BLK_SIZE])
                    continue

                self.write(data[blk:length])

        return 0

    def sxb_execute(self, address, a_reg=0, x_reg=0, y_reg=0, processor_flags=0x76):
        """ execute the program at the starting address, with the A/X/Y/Processor flags set

        Args:
            address (int): address to start execution
            a_reg (int): starting value of the A register
            x_reg (int): starting value of the X register
            y_reg (int): starting value of the Y register
            processor_flags (int): starting value of the processor flags
                65C816: Overflow | 8-bit Memory Select | 8-bit Index Register Select | Decimal Mode | IRQ Disable
                65C02:  Overflow | Unused | BRK | Decimal | IRQ Disable
        Returns:
            bool: true if submission was successful or false if not
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
            int(self.emulation),             # Emulation Off/On
            0,                          # Program Bank Register
            0                           # Data Bank Register
        )

        self.sxb_write(processor_state, self.mon_ram)
        return self.sxb_command(EXEC, length=1)

    def sxb_read(self, length: int, address=None):
        """reads length bytes of memory starting from address (if given)

        Args:
            length (int):  length of memory to read
            address (int): the address to read the memory

        Returns:
            bytes/bytearray: bytes of data read
        """
        if address:
            self.sxb_command(READ, address=address, length=length)

        if length < BLK_SIZE:
            return_data = self.read(length)
            return return_data

        return_data = bytearray(length)

        for blk in range(0, length, BLK_SIZE):
            if blk + BLK_SIZE < length:
                return_data[blk: blk + BLK_SIZE] = self.read(BLK_SIZE)
                continue
            return_data[blk:length] = self.read(length-blk)

        return return_data

    def sxb_load(self, file_path):
        """Load rom image

        Args:
            file_path (string): path to rom image

        Returns:
            list: the start address and length of the executable code

        Raises:
            ValueError: if the rom does not have 0x5A at the begging signifying
                rom was not compiled/assembled with the -g flag
        """
        with open(file_path, 'rb') as fh:
            rom_data = fh.read()

        if rom_data[0] == 0x5a:     # checking for SXB flag symbol from the WDC assembler/Compiler

            code_address = self.decode(rom_data[1:4])
            code_length = self.decode(rom_data[4:6])
            code = rom_data[7:7+code_length]
            self.sxb_write(code, code_address)
            return code_address, code_length

        raise ValueError("Program needs to be compiled/assembled with the -g option")
