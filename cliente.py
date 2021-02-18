import socket
from time import sleep
import sys
from libs.common import *
import os
import math
import constants as const
import ipaddress


class TCPClient:
    def __init__(self, ip, port, file_name, file_size, ip_version):
        self.server_ip = ip
        self.file = open(file_name, "rb")
        self.file_size = file_size
        self.file_name = file_name.split("/")[-1]
        self.port = port
        self.ip_version = ip_version

    def __receive_response(self, sock, raw=False, print_response=True, timeout=False):
        if timeout:
            sock.settimeout(timeout)
        try:
            response = sock.recv(1024)
            if print_response:
                print(f"<-- Received: {response}")
        except Exception as e:
            print("No response:",  e)
            response = b""
        finally:
            return response if raw else str(response, "ascii")

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
        sock_version = socket.AF_INET if self.ip_version == 4 else socket.AF_INET6
        udp_sock = socket.socket(sock_version,  # Internet
                                 socket.SOCK_DGRAM)  # UDP
        i = 0
        packet_count = math.ceil(self.file_size / 1000)
        packets_status = dict.fromkeys(range(packet_count),
                                       {"status": 0, "payload": b'', "size": 0})
        end_transmition = False
        while not end_transmition:
            if i == packet_count:
                end_transmition = True
                break
            for seq_number in range(i, min(i+const.window_size, packet_count)):
                print("[DEBUG] Trying to send Packet: ", seq_number, " | i:", i)
                if packets_status[seq_number]["status"] == 0:
                    packet_payload, packet_size = self.__get_file_chunk()
                    packets_status.update({seq_number: {"status": 1, "payload": packet_payload, "size": packet_size}})
                if packets_status[seq_number]["status"] == 1:
                    packet = b'06' + seq_number.to_bytes(4, 'big') \
                             + packets_status[seq_number]["size"].to_bytes(2, 'big') \
                             + packets_status[seq_number]["payload"]
                    print(f"--> Sending packet {seq_number+1}/{packet_count}")
                    udp_sock.sendto(packet, (self.server_ip, udp_port))
                ack = self.__receive_response(tcp_sock, raw=True,
                                              print_response=False, timeout=1e-2)
                if len(ack) > 0 and int(ack[:2]) == 7:
                    ack_seq_number = int.from_bytes(ack[2:], 'big')
                    packets_status[ack_seq_number]["status"] = 2
                    if ack_seq_number == i:
                        i += 1
        udp_sock.close()
        print("Done")

    def connect(self):
        sock_version = socket.AF_INET if self.ip_version == 4 else socket.AF_INET6
        with socket.socket(sock_version, socket.SOCK_STREAM) as sock:
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
                if msg_id_code == 8:
                    print("Invalid name. Max size: 15bytes")
                    sock.close()
                    return -1


if __name__ == "__main__":
    if len(sys.argv) != 4:
        usage("client", sys.argv[0])

    ip_version = ipaddress.ip_address(sys.argv[1]).version
    ip, port, file_name = str(ipaddress.ip_address(sys.argv[1])), int(sys.argv[2]), sys.argv[3]
    file_size = os.path.getsize(file_name)

    client = TCPClient(ip, port, file_name, file_size, ip_version)
    client.connect()
