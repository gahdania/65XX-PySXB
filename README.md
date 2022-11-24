# PySXB
Simplified Interface for the WDC development boards

## Installation

OS X & Linux:

    pip install PySXB

Clone the latest version at [Repo][gitlab]

## Usage Example
    from PySXB.pysxb import PySXB
    sxb = PySXB('/dev/ttyUSB0')

    # load a program into memory
    sxb.sxb_load('/path/to/binary')

    # Read from the stack
    sxb.sxb_read(0x0100, 256)

    # Write to zero page
    sxb.sxb_write(<data>, 0x0000)

    # execute a program or statement with the A register with a value of 0x10
    sxb.sxb_execute(0x2000, a_reg=0x10)    

    # to print the formatted output of the zero page
    sxb.hex(sxb.read(0x0000, 256))
    

For more information, please the [wiki][wiki]

## Release History
Please change log for complete history

## Meta

David "Gahd" Couples – [@gahdania][twitter] – gahdania@gahd.io

Distributed under the GPL v3+ license. See ``LICENSE`` for more information.

[PySXB on Gitlab][gitlab]

## Contributing

1. [Fork it][fork]
2. Create your feature branch (`git checkout -b feature/fooBar`)
3. Commit your changes (`git commit -am 'Add some fooBar'`)
4. Push to the branch (`git push origin feature/fooBar`)
5. Create a new Pull Request

<!-- Markdown link & img dfn's -->
[wiki]: https://battlenet1.gitlab.io/battlenet-client
[twitter]: https://twitter.com/gahdania
[gitlab]: https://gitlab.com/65cxxx/pysxb.git
[fork]: https://gitlab.com/65cxxx/pysxb/-/forks/new
[header]: https://gilab.com/