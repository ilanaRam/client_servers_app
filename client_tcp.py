import multiprocessing
import queue
import socket
from typing import Final # makes my types be final without ability to change their type


class Client:
    ############################################################################################
    # CLIENT SOCKET:
    # create socket -> connect (to server) -> send data (to server) -> receive answer (from server)

    # !! Pay attention connect the Client only after Server already connected and listening

    # here we will use ECHO Server that will always answer upon connect to it
    ############################################################################################
    def __init__(self, ip = None, port = None):
        self.ip: Final[str] = "127.0.0.1" if not ip else ip
        self.port: Final[int] = 8820 if not port else port

        self.MAX_CONNECTIONS: Final[int] = 1
        self.MAX_DATA_SIZE: Final[int] = 1024  # 1KB
        self.CLIENT: Final[str] = "CLIENT"
        self.client_socket = None
        self.server_responses_queue = multiprocessing.Queue()
        self.responses_store = {}

        self.connect()

    def connect(self):
        # 1. create client socket
        print(f"[{self.CLIENT}]: Creating the socket ...")
        self.client_socket = socket.socket(socket.AF_INET,     # this means we use protocol IP (our socket will expect to connect between 2 IP addresses
                                           socket.SOCK_STREAM) # this means we use protocol TCP (in charge of reliable connection)

        # 2. connect socket to server (method connect() receives a tuple with (IP of the server, PORT of the server))
        # because the fact that the client and the server are both on the same PC the ip is a local host address 127.0.0.1
        print(f"[{self.CLIENT}]: Creating the Connection (=connecting the socket to) with ip: {self.ip}, port: {self.port} ...")
        self.client_socket.connect((self.ip, self.port))


    def receive_loop(self):
        message_id = 0

        # receiving loop
        while True:
            try:
                print(f"[{self.CLIENT}]: Waiting for response from the server ...")
                # receive
                received_data = self.client_socket.recv(self.MAX_DATA_SIZE) # we need to define MAX bytes we allow to extract from the socket - here we say max 1024 bytes (1K) if will be less ok
                if not received_data:
                    break
                response_from_server = received_data.decode('utf-8')
                print(f"[{self.CLIENT}]: Received message from the server: <{response_from_server}>")

                self.responses_store.setdefault(message_id,[]).append(response_from_server)
                message_id += 1
            except:
                break

    def start(self):
        """
        Client works in a sequential manner - works like a chat:
        1. GET message from user
        2. SEND message to server
        3. WAIT for response
        4. SHOW received message
        5. REPEAT
        :return:
        """
        while True:
            # GET
            message = input("Please enter message: ").rstrip()
            # check input
            if not message:
                print(f"[{self.CLIENT}]: Empty message is ignored")
            else:
            # SEND
                self.send(message) # send any message to server (either 'q' or not, as message 'q' tels the server to finish)
                if message == 'q':
                    return
                # WAIT + RECEIVE
                self.receive()

    def send(self, message):
        # 3. actual sending of the data to the server
        print(f"[{self.CLIENT}]: Sending message: {message} to Server ..")
        self.client_socket.sendall(message.encode())
        print(f"[{self.CLIENT}]: Message was sent")

    def receive(self):
        # Client waits to get the answer from the server
        # we need to define MAX bytes we allow to extract from the socket - here we say max 1024 bytes (1K) if will be less ok
        print(f"[{self.CLIENT}]: Waiting for response from the server ...")
        received_data = self.client_socket.recv(self.MAX_DATA_SIZE).decode()  # blocking operation, client will not send next message before he got respond to the current message
        print(f"[{self.CLIENT}]: Received message from the server: <{received_data}>")

    def disconnect(self):
        print(f"[{self.CLIENT}]: Closing the SOCKET (connection) ....")
        self.client_socket.close()
        print(f"[{self.CLIENT}]: SOCKET (connection) is closed")


# I added here a main just in case I wish to run the client directly and not from simpl_client_server_app.py
if __name__ == '__main__':
    ip: Final[str] = "127.0.0.1"
    port: Final[int] = 8820

    client = Client(ip, port)

    # start sending (& receiving responds)
    client.start()

    print(f"Client shutting down ")
    client.disconnect()


