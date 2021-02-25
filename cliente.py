import socket
from time import sleep
import sys
from libs.common import *
import os
import math
import constants as const
import ipaddress
import random


class TCPClient:
    def __init__(self, ip, port, file_name, file_size, ip_version):
        self.server_ip = ip
        self.file = open(file_name, "rb")
        self.file_size = file_size
        self.file_name = file_name.split("/")[-1]
        self.port = port
        self.ip_version = ip_version

    def __receive_response(self, sock, raw=False, print_response=True, timeout=False, debug=False):
        if timeout:
            sock.settimeout(timeout)
        try:
            response = sock.recv(1024)
            if print_response:
                print(f"<-- Received: {response}")
        except Exception as e:
            if debug:
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

    def __udp_file_preprocess(self):
        packet_count = math.ceil(self.file_size / 1000)
        packets_status = dict.fromkeys(range(packet_count),
                                       {"status": 0, "payload": b'', "size": 0})
        return packet_count, packets_status

    def __udp_define_window(self, i, total):
        return range(i, min(i + const.window_size, total))

    def __udp_initialize_packet(self, seq):
        packet_payload, packet_size = self.__get_file_chunk()
        self.packets_status.update(
            {seq: {"status": 1, "payload": packet_payload, "size": packet_size}})

    def __udp_preprocess_packet(self, seq):
        return b'06' + seq.to_bytes(4, 'big') \
        + self.packets_status[seq]["size"].to_bytes(2, 'big') \
        + self.packets_status[seq]["payload"]

    def __handle_udp_transfer(self, server_ip, udp_port, tcp_sock):
        # Start UDP server
        print(f"--> Sending user datagram protocol file on <{server_ip}>:"
              f"<{udp_port}>")
        sock_version = socket.AF_INET if self.ip_version == 4 else socket.AF_INET6
        udp_sock = socket.socket(sock_version,  # Internet
                                 socket.SOCK_DGRAM)  # UDP

        # Start file transfer
        first_in_window = 0
        acks_pending = 0
        packet_count, self.packets_status = self.__udp_file_preprocess()
        while first_in_window < packet_count or acks_pending > 0:
            for seq_number in self.__udp_define_window(first_in_window, packet_count):
                # print(f"[DEBUG]Sending: {seq_number} | i: {first_in_window} | status: {self.packets_status[seq_number]['status']}")
                if seq_number == first_in_window and self.packets_status[seq_number]["status"] == 2:
                    first_in_window += 1
                if self.packets_status[seq_number]["status"] == 0:  # Load packet
                    self.__udp_initialize_packet(seq_number)
                    acks_pending += 1
                if self.packets_status[seq_number]["status"] == 1:  # Send packet
                    packet = self.__udp_preprocess_packet(seq_number)
                    print(f"--> Sending packet {seq_number+1}/{packet_count}")
                    # if random.random() > .8:
                    #     packet = packet.replace(b's', b'')
                    # if random.random() < .8: TODO: REMOVER
                    udp_sock.sendto(packet, (self.server_ip, udp_port))

                ack = self.__receive_response(tcp_sock, raw=True, print_response=False,
                                              timeout=const.udp_timeout)
                if len(ack) > 0 and int(ack[:2]) == 7:  # Receive ack and mark correspondent packet as ok
                    ack_seq_number = int.from_bytes(ack[2:], 'big')
                    self.packets_status[ack_seq_number]["status"] = 2
                    acks_pending -= 1
        udp_sock.close()

    def connect(self):
        sock_version = socket.AF_INET if self.ip_version == 4 else socket.AF_INET6
        with socket.socket(sock_version, socket.SOCK_STREAM) as sock:
            sock.connect((self.server_ip, self.port))
            print("Client connected")
            self.__send_request("01", sock)

            while True:
                response = self.__receive_response(sock)
                if len(response) >= 2:
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
                        print("Invalid file name. Max size: 15bytes")
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
