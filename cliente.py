import socket
from time import sleep
import sys
from libs.common import *
import os
import math


class TCPClient:
    def __init__(self, ip, port, file_name, file_size):
        self.server_ip = ip
        self.file = open(file_name, "rb")
        self.file_size = file_size
        self.file_name = file_name.split("/")[-1]
        self.port = port

    def __get_file_chunk(self, buf=1000):
        data = self.file.read(buf)
        return data, len(data)

    def __send_request(self, msg, sock):
        response = bytes(f"{msg}", 'ascii')
        print(f"Sending: {msg}")
        sock.sendall(response)

    def __request_info_file(self, res, sock):
        udp_port = int(res[2:6])
        self.__send_request("03" + self.file_name + str(self.file_size), sock)
        return udp_port

    def connect(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((self.server_ip, self.port))
            print("client connected")
            self.__send_request("01", sock)

            while True:
                response = str(sock.recv(1024), 'ascii')
                print(f"Received: {response}")
                msg_id_code = int(response[:2])
                if msg_id_code == 2:
                    udp_port = self.__request_info_file(response, sock)
                if msg_id_code == 4:
                    print(f"sending data file on <{self.server_ip}>:"
                          f"<{udp_port}>")
                    udp_sock = socket.socket(socket.AF_INET,  # Internet
                                         socket.SOCK_DGRAM)  # UDP
                    i = 1
                    while True:
                        file_chunk, file_chunk_size = self.__get_file_chunk()
                        if file_chunk_size == 0:
                            break
                        else:
                            print(f"packet {i}/{math.ceil(self.file_size/1000)}")
                            udp_sock.sendto(file_chunk, (self.server_ip, udp_port))
                            i += 1
                    udp_sock.close()
                    print("Done")
                if msg_id_code == 5:
                    print("closing connection")
                    sock.close()
                    return 0


if __name__ == "__main__":
    if len(sys.argv) != 4:
        usage("client", sys.argv[0])

    ip, port, file_name = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    file_size = os.path.getsize(file_name)

    client = TCPClient(ip, port, file_name, file_size)
    client.connect()
