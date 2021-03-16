import sys


def usage(alias, file):
    if alias == "client":
        print("usage:", file, "<host> <port> <file>")
    elif alias == "server":
        print("usage:", file, "<port> <ip_version (v4|v6)> <debug [optional] (expected: 1)>")
    sys.exit(1)


def message_event(msg, sock):
    print("sending", repr(msg))
    return sock.send(msg)
