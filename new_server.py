import libs.socketserver
import socket
import threading
import socketserver
from time import sleep
import socket
import sys
from libs.common import *
import random


class ThreadedTCPRequestHandler(socketserver.BaseRequestHandler):
    def __init__(self, request, client_address, server):
        super().__init__(request, client_address, server)

    def __send_response(self, msg):
        response = bytes(f"{msg}", 'ascii')
        print(f"Sending to <{self.cur_thread.name}>: {msg}")
        self.request.sendall(response)

    def __response_connection(self):
        udp_port = self.__set_random_udp_port((str,))
        self.__send_response("02" + udp_port)

    def __response_ok(self):
        self.__send_response("04")

    def __set_random_udp_port(self, fmts=(int,)):
        while True:
            random_port = random.randint(3000, 9999)
            if random_port not in server.udp_port_list:
                server.udp_port_list.append(random_port)
                break
        return str(random_port) if str in fmts else random_port
        # FIXME remover porta após fim do uso, obviamente... se der tempo

    # TODO remover todos os *no inspection*
    # noinspection PyAttributeOutsideInit
    def handle(self):
        self.cur_thread = threading.current_thread()
        while server.alive:
            data = str(self.request.recv(1024), 'ascii')
            print(f"Received from <Thread {self.cur_thread.name}>: '{data}'")
            msg_id_code = int(data[:2])
            if msg_id_code == 1:
                self.__response_connection()
            if msg_id_code == 3:
                self.__response_ok()


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    def __init__(self, addr, handler):
        super().__init__(addr, handler)
        self.alive = True
        self.udp_port_list = []


if __name__ == "__main__":
    if not hasattr(socket, 'SO_REUSEPORT'):
        socket.SO_REUSEPORT = 15

    if len(sys.argv) != 2:
        usage("server", sys.argv[0])

    host, port = '127.0.0.1', int(sys.argv[1])

    server = ThreadedTCPServer((host, port), ThreadedTCPRequestHandler)
    with server:
        # Start a thread with the server -- that thread will then start one
        # more thread for each request
        server_thread = threading.Thread(target=server.serve_forever)
        # Exit the server thread when the main thread terminates
        server_thread.daemon = True
        server_thread.start()
        print("Server loop running in thread:", server_thread.name)
        while server.alive:
            sleep(5)
    server.shutdown()
