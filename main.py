import getopt
import sys
from serial import SerialTimeoutException

from PySXB.pysxb import PySXB


if __name__ == "__main__":

    argv = sys.argv[1:]
    device = None
    baud = None
    file = None
    cpu_mode = None
    exec_address = None
    opts = []
    short_opts = "d:b:f:e:E:"
    long_opts = ("device =", "baud =", "file =", "C02 =", "C816 =")
    try:
        opts, opt_args = getopt.getopt(argv, short_opts, long_opts)
    except getopt.GetoptError as opt_error:
        print(f"Error: {opt_error}\n")

    for opt, opt_arg in opts:

        if opt in ('-d', '--device'):
            device = opt_arg

        if opt in ('-b', '--baud'):
            baud = opt_arg

        if opt in ('-f', '--file'):
            file = opt_arg

        if opt in ('-e', '--C02'):
            cpu_mode = 2       #
            exec_address = opt_arg

        if opt in ('-E', '--C816'):
            cpu_mode = 1
            exec_address = opt_arg

    # set defaults for needed variables
    if not device:
        device = '/dev/ttyUSB0'

    if not baud:
        baud = 9600

    if not cpu_mode:
        cpu_mode = 1

    ser = PySXB(device, baud)

    if file:
        ser.load_program(file)

    try:
        ser.execute(cpu_mode, 0x2000, 2)       # equivalent to F9 in debugger w/o break points
    except KeyboardInterrupt:
        sys.exit()
    except SerialTimeoutException as error:
        print(f"Error: {error}")
        sys.exit(1)
    else:
        print("End!")
