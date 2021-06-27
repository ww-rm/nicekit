import sys
import string


def _hexChunk(fp, size=16):
    """return a generator of two-tuple
    (hex_bytes, printable_bytes)

    fp: file object open with bin mode
    size: bytes read each time
    """

    _printable_bytes = string.printable.encode()
    _whitespace_bytes = string.whitespace.encode()
    chunk = fp.read(size)
    while chunk:
        hex_bytes = []
        printable_bytes = []

        for i in range(len(chunk)):
            byte = chunk[i:i+1]
            if i*2 == size:
                hex_bytes.append("")
            hex_bytes.append(byte.hex())

            if byte in _printable_bytes and byte not in _whitespace_bytes:
                printable_bytes.append(byte.decode())
            else:
                printable_bytes.append(".")

        yield (" ".join(hex_bytes), "".join(printable_bytes))
        chunk = fp.read(size)


def _rawChunk(fp):
    """return a generator of bytes row by row"""

    chunk = fp.readline().strip("\n")  # type: str
    while chunk:
        cmt_pos = chunk.find("//")
        chunk = chunk[0:None if cmt_pos < 0 else cmt_pos]
        try:
            raw_bytes = bytes.fromhex(chunk)
        except ValueError:
            return
        yield raw_bytes
        chunk = fp.readline().strip("\n")


def raw2hex(ifname, ofname=None):
    if not ofname:
        ofname = ifname + ".hex"
    try:
        with open(ifname, "rb") as in_f:
            with open(ofname, "w") as out_f:
                chunks = _hexChunk(in_f)
                for chunk in chunks:
                    out_f.write(chunk[0])
                    out_f.write("  // ")
                    out_f.write(chunk[1])
                    out_f.write("\n")
    except FileNotFoundError:
        print("No such file or directory: '%s'" %ifname)


def hex2raw(ifname, ofname=None):
    if not ofname:
        ofname = ifname + ".bin"
    try:
        with open(ifname, "r") as in_f:
            with open(ofname, "wb") as out_f:
                chunks = _rawChunk(in_f)
                for chunk in chunks:
                    out_f.write(chunk)
    except FileNotFoundError:
        print("No such file or directory: '%s'" %ifname)


def hexer(ifname, ofname=None, mode="hex"):
    """A tool to transform hex and raw.
    --help: show this text
    --hex: raw to hex
    --raw: hex to raw
    
    usage:
    hexer --help
    hexer <--hex|--raw> <infilename> [outfilename]
    """
    if mode == "hex":
        raw2hex(ifname, ofname)
    elif mode == "raw":
        hex2raw(ifname, ofname)
    else:
        print("NameError: no mode named '%s'" %mode)


def main():
    help_doc = "Command is not correct, use '--help' to get more info."

    if len(sys.argv) == 2 and sys.argv[1] == "--help":
        print(hexer.__doc__)
        return
    elif len(sys.argv) == 3 and sys.argv[1].startswith("--"):
        hexer(sys.argv[2], mode=sys.argv[1][2:])
        return
    elif len(sys.argv) == 4 and sys.argv[1].startswith("--"):
        hexer(sys.argv[2], sys.argv[3], mode=sys.argv[1][2:])
        return

    print(help_doc)

if __name__ == "__main__":
    main()
