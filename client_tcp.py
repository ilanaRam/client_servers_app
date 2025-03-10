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

        self.connect_client()

    def connect_client(self):
        # 1. create client socket
        print(f"[{self.CLIENT}]: Creating the socket ...")
        self.client_socket = socket.socket(socket.AF_INET,     # this means we use protocol IP (our socket will expect to connect between 2 IP addresses
                                           socket.SOCK_STREAM) # this means we use protocol TCP (in charge of reliable connection)

        # 2. connect socket to server (method connect() receives a tuple with (IP of the server, PORT of the server))
        # because the fact that the client and the server are both on the same PC the ip is a local host address 127.0.0.1
        print(f"[{self.CLIENT}]: Creating the Connection (=connecting the socket to) with ip: {self.ip}, port: {self.port} ...")
        self.client_socket.connect((self.ip, self.port))

    def send_message(self, message):
        # 3. send data to the server
        print(f"[{self.CLIENT}]: Client will send message: {message} to Server ..")
        self.client_socket.send(message.encode())
        print(f"[{self.CLIENT}]: Message was sent")
        # 4. Client waits to get the answer from the server
        # we need to define MAX bytes we allow to extract from the socket - here we say max 1024 bytes (1K) if will be less ok
        print(f"[{self.CLIENT}]: Waiting to get answer from the server ...")
        received_data = self.client_socket.recv(self.MAX_DATA_SIZE).decode()
        print(f"[{self.CLIENT}]: Received data from the server: <{received_data}>")

    def disconnect_client(self):
        print(f"[{self.CLIENT}]: Closing the SOCKET (connection) ....")
        self.client_socket.close()
        print(f"[{self.CLIENT}]: SOCKET (connection) is closed")


# I added here a main just in case I wish to run the client directly and not from simpl_client_server_app.py
if __name__ == '__main__':
    ip: Final[str] = "127.0.0.1"
    port: Final[int] = 8820

    client = Client(ip, port)
    while True:
        message = input("Enter message (empty message to exit):").rstrip()

        if message == 'q':
            client.send_message(message)
            break
        elif not message:
            print(f"User enter empty message")
            continue
        print(f"Message to send to server: {message}")
        client.send_message(message)

    print(f"Client shutting down ")
    client.disconnect_client()


