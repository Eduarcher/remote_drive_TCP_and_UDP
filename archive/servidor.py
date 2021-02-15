import socket
import selectors
import types
from libs.common import *
import random

encoding = 'utf-8'


class ServerTCPSocket:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.lsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        self.lsock.bind((host, port))
        self.lsock.listen()
        self.lsock.setblocking(False)
        print("listening on", (host, port))

    @staticmethod
    def get_file_name_and_size(buf):
        splits = str(buf.decode(encoding)).split('.')
        print(splits)
        filename = splits[0] + "." + splits[1][:3]
        filesize = int(splits[1][3:])
        return filename, filesize


class EventHandler:
    def __init__(self, sock, max_bytes_recv=1000):
        self.sel = selectors.DefaultSelector()
        self.sel.register(sock.lsock, selectors.EVENT_READ, data=None)
        self.server_sock = sock
        self.max_bytes_recv = max_bytes_recv
        self.udp_ip = "localhost"
        self.udp_port_list = [self.server_sock.port]

    def get_events(self):
        return self.sel.select(timeout=None)

    def set_random_udp_port(self):
        while True:
            random_port = random.randint(3000, 9999)
            if random_port not in self.udp_port_list:
                self.udp_port_list.append(random_port)
                return random_port

    def service_connection(self, key, mask):
        sock = key.fileobj
        data = key.data
        if mask & selectors.EVENT_READ:
            recv_data = sock.recv(self.max_bytes_recv)  # Should be ready to read
            if recv_data:
                data.outb += recv_data
            else:
                print('closing connection to', data.addr)
                self.sel.unregister(sock)
                sock.close()
        if mask & selectors.EVENT_WRITE:
            if data.outb:
                code = int(data.outb[:2])
                print('received code (', code, ') from:', data.addr, sep="")
                if code == 1:
                    self.udp_port = self.set_random_udp_port()
                    msg = "02" + str(self.udp_port)
                    sent = message_event(str.encode(msg), sock)
                    data.outb = data.outb[sent:]
                if code == 3:
                    # Prepare reception for file
                    if len(data.outb) > 25:
                        sent = message_event(b'09', sock)  # Name too large
                    else:
                        file_name, file_size = self.server_sock.__get_file_name_and_size(data.outb[2:])
                        print("File: ", file_name, file_size)

                        # Open UDP server
                        udp_sock = socket.socket(socket.AF_INET,  # Internet
                                             socket.SOCK_DGRAM)  # UDP
                        udp_sock.bind((self.udp_ip, self.udp_port))

                        # Send ok
                        sent = message_event(b'04', sock)

                        # Receive
                        received = 0
                        f = open("output/" + file_name, "wb")
                        while received < file_size:
                            file_chunk_data, udp_addr = udp_sock.recvfrom(file_size)
                            received += len(file_chunk_data)
                            print("Receiving data chunk. Size: ", len(file_chunk_data))
                            f.write(file_chunk_data)
                        print("Completed")
                        f.close()
                    data.outb = ''

    def accept_wrapper(self, sock):
        conn, addr = sock.accept()  # Should be ready to read
        print('accepted connection from', addr)
        conn.setblocking(False)
        data = types.SimpleNamespace(addr=addr, inb=b'', outb=b'')
        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        self.sel.register(conn, events, data=data)

    def close(self):
        self.sel.close()


if __name__ == '__main__':
    if not hasattr(socket, 'SO_REUSEPORT'):
        socket.SO_REUSEPORT = 15

    if len(sys.argv) != 2:
        usage("client", sys.argv[0])

    host, port = 'localhost', int(sys.argv[1])
    server_sock = ServerTCPSocket(host, port)
    event_handler = EventHandler(server_sock)

    try:
        while True:
            events = event_handler.get_events()
            for key, mask in events:
                if key.data is None:
                    event_handler.accept_wrapper(key.fileobj)
                else:
                    event_handler.service_connection(key, mask)
    except KeyboardInterrupt:
        print("caught keyboard interrupt, exiting")
    finally:
        event_handler.close()
