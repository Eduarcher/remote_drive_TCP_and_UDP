import socket
import selectors
import types
from libs.common import *
import os
import math

from time import sleep

encoding = 'utf-8'


class ClientTCPSocket:
    def __init__(self, host, port, file_to_transfer):
        self.server_addr = (host, port)
        print("starting connection to", self.server_addr)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setblocking(False)
        self.file = open(file_to_transfer, "rb")
        self.file_name = file_to_transfer.split("/")[-1]
        self.file_size = os.path.getsize(file_to_transfer)

    def start_connection(self):
        self.sock.connect_ex(self.server_addr)
        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        data = types.SimpleNamespace(
            msg_total=2,
            recv_total=0,
            message=b"01",
            outb=b"",
        )
        sel.register(self.sock, events, data=data)

    def get_file_chunk(self, buf=1000):
        data = self.file.read(buf)
        return data, len(data)

    def service_connection(self, key, mask):
        sock = key.fileobj
        data = key.data
        if mask & selectors.EVENT_READ:
            recv_data = sock.recv(1024)
            if recv_data:
                print("received", repr(recv_data))
                data.recv_total += len(recv_data)
            if data.recv_total >= 2:
                code = int(recv_data[:2])
                print("Code:", code)
                if code == 2:
                    # send file info
                    self.utp_port = int(recv_data[2:6])
                    msg = "03" + self.file_name + str(self.file_size)
                    sent = message_event(str.encode(msg), sock)
                if code == 4:
                    # send file data
                    print(f"sending data file on <{self.server_addr[0]}>:<{self.utp_port}>")
                    udp_sock = socket.socket(socket.AF_INET,  # Internet
                                         socket.SOCK_DGRAM)  # UDP
                    i = 1
                    while True:
                        sleep(2)
                        file_chunk, file_chunk_size = self.get_file_chunk()
                        if file_chunk_size == 0:
                            break
                        else:
                            print(f"packet {i}/{math.ceil(self.file_size/1000)}")
                            udp_sock.sendto(file_chunk, (self.server_addr[0], self.utp_port))
                            i += 1
                    udp_sock.close()
                    print("Done")
                if code == 5:
                    print("closing connection")
                    sel.unregister(sock)
                    sock.close()
        if mask & selectors.EVENT_WRITE:
            if data.message:
                print("sending", repr(data.message))
                sent = sock.send(data.message)
                data.message = data.message[sent:]


if __name__ == '__main__':
    if len(sys.argv) != 4:
        usage("client", sys.argv[0])

    sel = selectors.DefaultSelector()
    host, port, filename = sys.argv[1:4]
    client_sock = ClientTCPSocket(host, int(port), filename)
    client_sock.start_connection()

    try:
        while True:
            events = sel.select(timeout=1)
            if events:
                for key, mask in events:
                    client_sock.service_connection(key, mask)
            if not sel.get_map():
                break
    except KeyboardInterrupt:
        print("caught keyboard interrupt, exiting")
    finally:
        sel.close()
