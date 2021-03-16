import libs.socketserver as socketserver
import threading
from time import sleep
import socket
from libs.common import *
import random
import constants as const
from libs import testing_tools
from pathlib import Path

encoding = 'ascii'
debug_mode = False


class ThreadedTCPRequestHandler(socketserver.BaseRequestHandler):
    """
    Threaded child class responsible for handling a user file transference.
    Inheriting from socket server.
    """
    def __init__(self, request, client_address, server):
        super().__init__(request, client_address, server)

    def __send_response(self, msg):
        """
        General use function for sending messages to the client
        :param msg: message to send, if not in bytes will be converted via ascii
        """
        print(f"Sending to <{self.cur_thread.name}>: {msg}")
        if type(msg) != bytes:
            msg = bytes(f"{msg}", "ascii")
        self.request.sendall(msg)

    def __response_connection(self):
        """
        Response for starting connection and sending udp_port
        """
        self.udp_port = self.__set_random_udp_port()
        self.__send_response("02" + str(self.udp_port))

    def __response_ok(self):
        """
        Response to "OK" the file transference start
        """
        self.__send_response("04")

    def __response_ack(self, seq):
        """
        Response to acknowledge a packet receiving
        """
        seq_b = seq.to_bytes(4, 'big')
        self.__send_response(b"07" + seq_b)

    def __response_end(self):
        """
        Response for ending the transference
        """
        if debug_mode:
            testing_tools.compare_files("input", "output")  # Compare if files are right
        server.udp_port_list.remove(self.udp_port)  # Remove port from occupied list
        self.__send_response("05")

    @staticmethod
    def __set_random_udp_port(fmts=(int,)):
        """
        Define a random UDP port to the user, each user gets one
        :param fmts: fmt to return the port (default: int)
        :return: UDP Port
        """
        while True:
            random_port = random.randint(3000, 9999)
            if random_port not in server.udp_port_list:
                server.udp_port_list.append(random_port)
                break
        return str(random_port) if str in fmts else random_port

    @staticmethod
    def __get_file_name_and_size(req):
        """
        Gets the file name and size from the request, splitting according to "."
        :param req: request in bytes
        :return: file name and size
        """
        splits = req.split('.')
        print(splits)
        filename = splits[0] + "." + splits[1][:3]
        filesize = int(splits[1][3:])
        return filename, filesize

    @staticmethod
    def __unpack(packet):
        """
        Unpack a bytes packet and gets header data
        :param packet: packet to unpack
        :return: packets header values and payload
        """
        seq_number = int.from_bytes(packet[2:6], 'big')
        payload_size = int.from_bytes(packet[6:8], 'big')
        payload_data = packet[8:]
        payload_received_size = len(payload_data)
        return seq_number, payload_size, payload_data, payload_received_size

    @staticmethod
    def __verify_buffer(latest_packet, buffer, file):
        """
        Check the buffer and write pending packets
        :param latest_packet: seq_number of the latest packet written
        :param buffer: packets buffer containing pending packets
        :param file: file to write
        :return: updated buffer latest written packet
        """
        while True:
            if latest_packet + 1 in buffer.keys():
                latest_packet += 1
                file.write(buffer[latest_packet])
                del buffer[latest_packet]
            else:
                break
        return latest_packet

    def __handle_udp_transfer(self, req):
        """
        Responsable for handling udp transference
        :param req: request with file name and size
        """
        # Prepare reception for file
        file_name, file_size = self.__get_file_name_and_size(req)
        print(f"File to be Received from <Thread {self.cur_thread.name}>: {file_name} | "
              f"Size: {file_size}")
        file_output = open(const.output_folder + file_name, "wb")

        # Open UDP server
        sock_version = socket.AF_INET if ip_version == 4 else socket.AF_INET6
        udp_sock = socket.socket(sock_version, socket.SOCK_DGRAM)
        udp_sock.bind((host, self.udp_port))
        self.__response_ok()

        # Receive
        received_size = 0   # Total data received so far
        packets_received = []  # Keep track of all packets received
        packets_buffer = {}  # Temporary store unordered packets
        latest_packet = -1  # Mark the latest received packet

        while received_size < file_size:
            packet = udp_sock.recv(file_size)
            if int(packet[:2]) == 6:  # Check if code is 6(FILE)
                # Unpack all info from packet
                seq_number, payload_size, payload_data, payload_received_size = self.__unpack(packet)
                print(f"Receiving data chunk from <Thread {self.cur_thread.name}>. "
                      f"Sequence Number: {seq_number}. Size: {payload_size} bytes")

                # Check if the latest packets are waiting in the buffer
                latest_packet = self.__verify_buffer(latest_packet, packets_buffer, file_output)

                # Verify packet integrity and if it's not repeated before saving
                if seq_number not in packets_received and payload_received_size == payload_size:
                    if seq_number == latest_packet + 1:  # Check if it's the latest packet
                        file_output.write(payload_data)  # Write directly, don't buffer
                        latest_packet += 1
                    else:
                        packets_buffer[seq_number] = payload_data  # Buffer unordered packet
                    packets_received.append(seq_number)
                    received_size += payload_size
                    self.__response_ack(seq_number)  # Ack received packet
        print(f"Completed UDP transfer from <Thread {self.cur_thread.name}>.\n"
              f"Total Received: {received_size} Bytes.")
        file_output.close()
        udp_sock.close()

    def handle(self):
        """
        Main handle for message receiving and response definition
        :return: 0 on success and -1 on error
        """
        self.cur_thread = threading.current_thread()
        while server.alive:
            try:
                request = str(self.request.recv(1024), "ascii")
                print(f"Received from <Thread {self.cur_thread.name}>: '{request}'")
                msg_id_code = int(request[:2])
                if msg_id_code == 1:
                    self.__response_connection()
                if msg_id_code == 3:
                    if len(request) > 25 or len(request) < 8:
                        self.__send_response("08")  # Name too large or too small
                        return -1
                    else:
                        self.__handle_udp_transfer(request[2:])
                        sleep(2)  # Don't end too quickly, let the client finish too.
                        self.__response_end()
                        return 0
            except Exception as e:
                print("Error on Handle: ", e)
                return -1


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    """
    Server main class. Inheriting from socketserver classes
    """
    def __init__(self, addr, handler):
        super().__init__(addr, handler)
        self.alive = True
        self.udp_port_list = []


if __name__ == "__main__":
    if not hasattr(socket, "SO_REUSEPORT"):  # Apply port reuse
        socket.SO_REUSEPORT = 15

    if len(sys.argv) < 2 or len(sys.argv) > 4:  # check for args
        usage("server", sys.argv[0])

    if len(sys.argv) == 4 and sys.argv[3] == '1':  # check if debug mode is on (see usage)
        debug_mode = True
        testing_tools.delete_files("output")

    # Define IP version
    if len(sys.argv) > 2:
        if sys.argv[2] in const.ipv4_aliases:
            ip_version = 4
        elif sys.argv[2] in const.ipv6_aliases:
            ip_version = 6
        else:
            print("Invalid server version. Use v4 or v6")
            sys.exit()
    else:
        ip_version = const.default_ip_version
    host, port = const.ip_host[ip_version], int(sys.argv[1])

    Path("output/").mkdir(parents=True, exist_ok=True)

    # Start server
    server = ThreadedTCPServer((host, port), ThreadedTCPRequestHandler)
    with server:
        # Start a thread with the server -- that thread will then start one
        # more thread for each request
        server_thread = threading.Thread(target=server.serve_forever)
        # Exit the server thread when the main thread terminates
        server_thread.daemon = True
        server_thread.start()
        print("Server loop running in thread:", server_thread.name, "and Port: ", port)
        while server.alive:  # Tag for ending server. Unused (no command to end server defined)
            sleep(2)
    server.shutdown()
