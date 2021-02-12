import sys


def usage(alias, file):
    if alias == "client":
        print("usage:", file, "<host> <port> <file>")
    elif alias == "server":
        print("usage:", file, "<port>")
    sys.exit(1)


def message_event(msg, sock):
    print("sending", repr(msg))
    return sock.send(msg)
