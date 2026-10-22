"""Read RESP array-of-bulk-string commands from a local incremental AOF.

This small file reader is independent of redis-py's network parser.
It supports the command representation of this controlled workload.
"""


def _length(stream, prefix):
    header = stream.readline()
    if (
        not header.startswith(prefix)
        or not header.endswith(b"\r\n")
        or not header[1:-2].isdigit()
    ):
        raise ValueError("Malformed AOF RESP length")
    return int(header[1:-2])


def read_command(stream):
    count = _length(stream, b"*")
    if count == 0:
        raise ValueError("Empty AOF command")
    command = []
    for _ in range(count):
        length = _length(stream, b"$")
        value = stream.read(length)
        if len(value) != length or stream.read(2) != b"\r\n":
            raise ValueError("Truncated AOF bulk string")
        command.append(value)
    return command
