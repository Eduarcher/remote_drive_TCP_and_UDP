import socket
from time import sleep
import sys
from libs.common import *
import os


class TCPClient:
    def __init__(self, ip, port, file_name, file_size):
        self.ip = ip
        self.file_size = file_size
        self.file_name = file_name
        self.port = port

    def connect(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((self.ip, self.port))
            print("client connected")
            msg = "01"
            sock.sendall(bytes(msg, 'ascii'))

            while True:
                response = str(sock.recv(1024), 'ascii')
                print(f"Received: {response}")
                msg_id_code = int(response[:2])
                if msg_id_code == 2:
                    utp_port = int(response[2:6])
                    msg = "03" + self.file_name + str(self.file_size)
                    sent = message_event(str.encode(msg), sock)


if __name__ == "__main__":
    if len(sys.argv) != 4:
        usage("client", sys.argv[0])

    ip, port, file_name = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    file_size = os.path.getsize(file_name)

    client = TCPClient(ip, port, file_name, file_size)
    client.connect()
