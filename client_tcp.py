import socket
from typing import Final # makes my types be final without ability to change their type
import yaml
import time
import ssl
import certs


class Client:
    ############################################################################################
    # CLIENT SOCKET:
    # create socket -> connect (to server) -> send data (to server) -> receive answer (from server)

    # !! Pay attention connect the Client only after Server already connected and listening

    # here we will use ECHO Server that will always answer upon connect to it
    ############################################################################################
    def __init__(self, ip = None, port = None):
        self.app: Final[str] = "CLIENT"
        # self.ip: Final[str] = "127.0.0.1" if not ip else ip
        # self.port: Final[int] = 8820 if not port else port

        self.client_socket = None
        self.connection_store = {}
        self.index = 0

        ip, port, max_retries, retry_delay, max_data_size = self.init()
        self.IP: Final[str] =  ip  # also possible to do: socket.gethostbyname(socket.gethostname())  # <---- this way we determine the local host address, this way -> we set it hard codded: "127.0.0.1" if not ip else ip
        print(f"[{self.app}]: app is executed using the next parameters: ")
        print(f"[{self.app}]: IP: {self.IP}")

        self.PORT: Final[int] = port # also possible to do: 8820 if not port else port
        print(f"[{self.app}]: PORT: {self.PORT}")

        self.max_retries = max_retries
        print(f"[{self.app}]: Max number of connection retries: {self.max_retries}")

        self.retry_delay = retry_delay
        print(f"[{self.app}]: Delay between retries: {self.retry_delay}")

        self.MAX_DATA_SIZE = max_data_size
        print(f"[{self.app}]: Max data size: {self.MAX_DATA_SIZE}")

        self.connect()

    def init(self):
        with (open("client_config.yaml", "r") as yaml_file):
            config = yaml.safe_load(yaml_file)
            return config["client"]["ip_address"],\
                   config["client"]["port"],\
                   config["client"]["max_retries"],\
                   config["client"]["retry_delay"], \
                   config["client"]["max_data_size"]

    def connect(self):
        # 1. create client 'regular' socket - this operation has nothing to do with Server (it doesnt requires a Server be connected)
        print(f"\n\n[{self.app}]: Creating the 'regular' socket ...")
        self.client_socket = socket.socket(socket.AF_INET,     # this means we use protocol IP (our socket will expect to connect between 2 IP addresses
                                           socket.SOCK_STREAM) # this means we use protocol TCP (in charge of reliable connection)
        print(f"[{self.app}]: 'regular' socket ... created")

        # 2. creating a context object that holds all relevant settings and configurations related to SSL/TLS secured connection
        print(f"[{self.app}]: Creating the secured SSL context (set of rules for secure connection) ...")
        # context = ssl.create_default_context() # <--- if I do it this way, I actually tell client to accept any cert from server, while server will by default create self signed certificate that will be by default rejected by python ssl so I need tell Client that will be sent specific self signed cert from server and please deal only with this one
        context = ssl.create_default_context(cafile="certs/ilana_cert_01.pem")# <--- if I do it this way, I actually tell client to verify specific self signed certificate
        print(f"[{self.app}]: default SSL context ... created")

        # since we use self-signed certificate, which is default, by default python ssl module will reject it so we must handle it:
        # Disable hostname verification, it is good while testing but in production we must replace this with: True
        context.check_hostname = False
        # this way we say: allow only this cert: 'certs/ilana_cert_01.pem',  or we can use ssl.CERT_NONE to make Client not check certificate at all
        context.load_verify_locations('certs/ilana_cert_01.pem')
        # context.verify_mode = ssl.CERT_NONE # Accept any certificate, it is good while testing but in production we must replace this with: CERT_REQUIRED

        print(f"[{self.app}]: Wrapping 'regular' socket with SSL")
        self.client_socket = context.wrap_socket(self.client_socket,server_hostname=self.IP) # if we set flag: context.check_hostname = False Server IP will not be checked
        print(f"[{self.app}]: socket is wrapped with TLS/SSL, TLS version is: {self.client_socket.version()}")

        # the correct order is:
        # 0. create ssl context
        # 1. create 'regular' socket
        # 2. wrap socket with ssl
        for connect_attempt in range(1, self.max_retries + 1):
            print(f"[{self.app}]: Attempting to connect Client to Server [{connect_attempt}], ip: {self.IP}, port: {self.PORT} ...")
            # 3. connect server - here socket already need to be ssl socket as Server side expects ssl socket !
            try:
                self.client_socket.connect((self.IP, self.PORT))
                print(f"[{self.app}]: Connected to the Server successfully !")
                break
            except (ConnectionRefusedError, socket.timeout):
                print(f"[{self.app}]: Server not up yet, retrying in {self.retry_delay} seconds...")
                time.sleep(self.retry_delay)
        else:
            print(f"[{self.app}]: Failed to connect to the Server after {self.max_retries} attempts ###")
            exit(1)  # Exit if connection never succeeded

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
                print(f"[{self.app}]: Empty message is ignored")
            else:
                self.send(message) # send any message to server (either 'q' or not, as message 'q' tels the server to finish)
                if message == 'q':
                    return
                self.receive()

    def send(self, message):
        # actual sending of the data to the server
        print(f"[{self.app}]: Sending message: {message} to Server ..")
        self.client_socket.sendall(message.encode())
        print(f"[{self.app}]: Message was sent")
        self.connection_store.setdefault(self.index,[]).append(message)

    def receive(self):
        # Client waits to get the answer from the server
        # we need to define MAX bytes we allow to extract from the socket - here we say max 1024 bytes (1K) if will be less ok
        print(f"[{self.app}]: Waiting for response from the server ...")
        received_data = self.client_socket.recv(self.MAX_DATA_SIZE).decode()  # blocking operation, client will not send next message before he got respond to the current message
        print(f"[{self.app}]: Received message from the server: <{received_data}>")
        self.connection_store.setdefault(self.index, []).append(received_data)
        self.index += 1

    def disconnect(self):
        print(f"[{self.app}]: Closing the SOCKET (connection) ....")
        self.client_socket.close()
        print(f"[{self.app}]: SOCKET (connection) is closed")

    def print_sent_messages(self):
        print(f"\n[{self.app}]: All the messages that were sent: Client -> Server\n"
              f"--------------------------------------------------------------------")
        for index, messages_list in self.connection_store.items():
            print(f"[{self.app}]: [{index}]: {messages_list}")

# I added here a main just in case I wish to run the client directly and not from simpl_client_server_app.py
if __name__ == '__main__':
    client = Client()
    client.start()

    print(f"Client shutting down ")
    client.disconnect()

    client.print_sent_messages()


