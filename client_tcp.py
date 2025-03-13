import socket
from typing import Final # makes my types be final without ability to change their type
import yaml


class Client:
    ############################################################################################
    # CLIENT SOCKET:
    # create socket -> connect (to server) -> send data (to server) -> receive answer (from server)

    # !! Pay attention connect the Client only after Server already connected and listening

    # here we will use ECHO Server that will always answer upon connect to it
    ############################################################################################
    def __init__(self, ip = None, port = None):
        self.CLIENT: Final[str] = "CLIENT"
        # self.ip: Final[str] = "127.0.0.1" if not ip else ip
        # self.port: Final[int] = 8820 if not port else port

        self.MAX_CONNECTIONS: Final[int] = 1
        self.MAX_DATA_SIZE: Final[int] = 1024  # 1KB

        self.client_socket = None

        self.connection_store = {}
        self.index = 0

        ip,port = self.init()
        self.IP: Final[str] =  ip  # also possible to do: socket.gethostbyname(socket.gethostname())  # <---- this way we determine the local host address, this way -> we set it hard codded: "127.0.0.1" if not ip else ip
        print(f"[{self.CLIENT}]: Using IP: {self.IP}")

        self.PORT: Final[int] = port # also possible to do: 8820 if not port else port
        print(f"[{self.CLIENT}]: Using PORT: {self.PORT}")

        self.connect()

    def init(self):
        with open("client_config.yaml", "r") as yaml_file:
            config = yaml.safe_load(yaml_file)
            return config["client"]["ip_address"], config["client"]["port"]

    def connect(self):
        # 1. create client socket
        print(f"[{self.CLIENT}]: Creating the socket ...")
        self.client_socket = socket.socket(socket.AF_INET,     # this means we use protocol IP (our socket will expect to connect between 2 IP addresses
                                           socket.SOCK_STREAM) # this means we use protocol TCP (in charge of reliable connection)
        # 2. connect socket to server (method connect() receives a tuple with (IP of the server, PORT of the server))
        self.client_socket.connect((self.IP, self.PORT))

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
        self.connection_store.setdefault(self.index,[]).append(message)

    def receive(self):
        # Client waits to get the answer from the server
        # we need to define MAX bytes we allow to extract from the socket - here we say max 1024 bytes (1K) if will be less ok
        print(f"[{self.CLIENT}]: Waiting for response from the server ...")
        received_data = self.client_socket.recv(self.MAX_DATA_SIZE).decode()  # blocking operation, client will not send next message before he got respond to the current message
        print(f"[{self.CLIENT}]: Received message from the server: <{received_data}>")
        self.connection_store.setdefault(self.index, []).append(received_data)
        self.index += 1

    def disconnect(self):
        print(f"[{self.CLIENT}]: Closing the SOCKET (connection) ....")
        self.client_socket.close()
        print(f"[{self.CLIENT}]: SOCKET (connection) is closed")

    def print_sent_messages(self):
        print(f"\n[{self.CLIENT}]: All the messages that were sent: Client -> Server\n"
              f"--------------------------------------------------------------------")
        for index, messages_list in self.connection_store.items():
            print(f"[{self.CLIENT}]: [{index}]: {messages_list}")

# I added here a main just in case I wish to run the client directly and not from simpl_client_server_app.py
if __name__ == '__main__':
    client = Client()
    client.start()

    print(f"Client shutting down ")
    client.disconnect()

    client.print_sent_messages()


