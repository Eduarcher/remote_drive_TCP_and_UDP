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

    def __receive_response(self, sock, raw=False, print_response=True):
        response = sock.recv(1024)
        if print_response:
            print(f"<-- Received: {response}")
        return response if not raw else str(response, "ascii")

    def __get_file_chunk(self, buf=1000):
        data = self.file.read(buf)
        return data, len(data)

    def __send_request(self, msg, sock):
        response = bytes(f"{msg}", "ascii")
        print(f"--> Sending: {msg}")
        sock.sendall(response)

    def __request_info_file(self, res, sock):
        udp_port = int(res[2:6])
        self.__send_request("03" + self.file_name + str(self.file_size), sock)
        return udp_port

    def __handle_udp_transfer(self, server_ip, udp_port, tcp_sock):
        print(f"--> Sending user datagram protocol file on <{server_ip}>:"
              f"<{udp_port}>")
        udp_sock = socket.socket(socket.AF_INET,  # Internet
                                 socket.SOCK_DGRAM)  # UDP
        i = 0
        while True:
            file_chunk, file_chunk_size = self.__get_file_chunk()
            if file_chunk_size == 0:
                break
            else:
                seq_number = i
                packet = b'06' + seq_number.to_bytes(4, 'big') \
                         + file_chunk_size.to_bytes(2, 'big') \
                         + file_chunk
                print(f"--> Sending packet {i+1}/{math.ceil(self.file_size / 1000)}")
                udp_sock.sendto(packet, (self.server_ip, udp_port))
                response = self.__receive_response(tcp_sock, True, False)
                i += 1
        udp_sock.close()
        print("Done")

    def connect(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((self.server_ip, self.port))
            print("Client connected")
            self.__send_request("01", sock)

            while True:
                response = self.__receive_response(sock)
                msg_id_code = int(response[:2])
                if msg_id_code == 2:
                    udp_port = self.__request_info_file(response, sock)
                if msg_id_code == 4:
                    self.__handle_udp_transfer(self.server_ip, udp_port, sock)
                if msg_id_code == 5:
                    print("Closing connection")
                    sock.close()
                    return 0


if __name__ == "__main__":
    if len(sys.argv) != 4:
        usage("client", sys.argv[0])

    ip, port, file_name = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    # ip, port, file_name = 'localhost', 6969, 'input/test.txt'
    file_size = os.path.getsize(file_name)

    client = TCPClient(ip, port, file_name, file_size)
    client.connect()
