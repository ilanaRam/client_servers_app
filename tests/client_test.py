import os

import pytest
from src.client_tcp import Client
import socket
from typing import Final # makes my types be final without ability to change their type
from typing import Final # makes my types be final without ability to change their type
import ssl
import yaml

class MockServer:
    def __init__(self):
        self.app: Final[str] = "TEST FOR CLIENT"
        self.mock_server_app: Final[str] = "MOCK_SERVER"
        # A simple secure Echo Server that sends back whatever it receives.
        print(f"[{self.app}]: Mocking the Server")
        # ----------------------------------------------------------
        ip, port, max_data_size = self._init()
        print(f"[{self.app}]: app is executed using the next parameters: ")
        self.IP: Final[
            str] = ip  # also possible to do: socket.gethostbyname(socket.gethostname()) if not ip else ip  # <---- this way we determine the local host address, this way -> we set it hard codded: "127.0.0.1" if not ip else ip
        print(f"[{self.app}]: IP: {self.IP}")

        self.PORT: Final[int] = port  # also possible to do: 8820 if not port else port
        print(f"[{self.app}]: PORT: {self.PORT}")

        self.MAX_DATA_SIZE = max_data_size
        print(f"[{self.app}]: Max data size: {self.MAX_DATA_SIZE}")

    def _find_full_file_path(self, filename):
        for dirpath, _, filenames in os.walk(os.getcwd()):
            if filename in filenames:
                full_file_path = os.path.join(dirpath, filename)  # Return full path if found
                return full_file_path
        return None  # Return None if not found

    def mock_echo_server(self):
        print(f"[{self.mock_server_app}]: Creating mock echo server socket ...")
        self.server_socket = socket.socket(socket.AF_INET,
                                      socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        print(f"[{self.mock_server_app}]: Creating SSL context  for my echo auto server ...")
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        # load certificate + key (certificate for authentication with Client, keys for encryption messages)
        print(f"[{self.mock_server_app}]: Load Authentication certificate and encryption keys, for secure connection ...")

        full_path_to_cert_file = self._find_full_file_path(Path.cwd().parent, "ilana_cert_01.pem")
        full_path_to_key_file = self._find_full_file_path(Path.cwd().parent, "ilana_key_01.pem")
        print(f"[{self.app}]: Loading cert + key files from: {full_path_to_cert_file}")
        context.load_cert_chain(certfile=full_path_to_cert_file,
                                keyfile=full_path_to_key_file)


        context.load_cert_chain(certfile="certs/ilana_cert_01.pem",
                                keyfile="certs/ilana_key_01.pem")
        print(f"[{self.mock_server_app}]: Wrapping the 'regular' TCP/IP socket to be SSL 'secured' socket ...")
        self.server_socket = context.wrap_socket(self.server_socket,
                                                 server_side=True)  # <--- this line tells python that this is a Server and not a Client
        self.server_socket.bind((self.IP, self.PORT))
        self.server_socket.listen(1)  # Allow 1 client

        print(f"[{self.mock_server_app}] @@@ Mock server started, waiting for connection @@@ ...")
        client_socket, client_address = self.server_socket.accept()
        print(f"[{self.mock_server_app}] Client connected from {client_address}")

        while True:
            print(f"[{self.mock_server_app}]: process 'receive & store & echo' is running ...")
            try:
                data = client_socket.recv(1024)  # Receive message from client
                if not data:
                    break
                client_socket.sendall(data)  # Send back the same message
            except Exception:
                break

        client_socket.close()
        self.server_socket.close()
        print("[MOCK SERVER] Server closed.")

    def _init(self):
        with open("../configs/server_config.yaml", "r") as yaml_file:
            config = yaml.safe_load(yaml_file)
            return config["server"]["ip_address"],\
                   config["server"]["port"], \
                   config["server"]["max_data_size"]

class TestCliemt:

    @pytest.fixture
    def files_obj(self):
        print("\n\n############### Client test - Started ###########")
        yield Client()
        print("\n############### Client test - Ended #############\n\n")