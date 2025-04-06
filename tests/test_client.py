import os
from pathlib import Path
import pytest
from src.client_tcp import Client
import threading
import socket
from typing import Final # makes my types be final without ability to change their type
import ssl
import yaml
import time

class MockServer:
    def __init__(self):
        self.client_socket = None
        self.server_socket = None
        self.server_thread = None

        self.app: Final[str] = "TEST FOR CLIENT"
        self.mock_server_app: Final[str] = "MOCK_SERVER"
        # A simple secure Echo Server that sends back whatever it receives.
        print(f"[{self.mock_server_app}]: starting the mock Server")
        # ----------------------------------------------------------
        ip, port, max_data_size = self._init()
        print(f"[{self.mock_server_app}]: app is executed using the next parameters: ")
        self.IP: Final[
            str] = ip  # also possible to do: socket.gethostbyname(socket.gethostname()) if not ip else ip  # <---- this way we determine the local host address, this way -> we set it hard codded: "127.0.0.1" if not ip else ip
        print(f"[{self.mock_server_app}]: IP: {self.IP}")

        self.PORT: Final[int] = port  # also possible to do: 8820 if not port else port
        print(f"[{self.mock_server_app}]: PORT: {self.PORT}")

        self.MAX_DATA_SIZE = max_data_size
        print(f"[{self.mock_server_app}]: Max data size: {self.MAX_DATA_SIZE}")

    def _init(self):
        full_path_to_file = self._find_full_file_path(Path.cwd().parent,"server_config.yaml")
        print(f"[{self.app}]: Loading configuration for the server from: {full_path_to_file}")
        if not full_path_to_file:
            raise FileExistsError

        with open(full_path_to_file, "r") as yaml_file:
            config = yaml.safe_load(yaml_file)
            return config["server"]["ip_address"],\
                   config["server"]["port"], \
                   config["server"]["max_data_size"]

    def _find_full_file_path(self, my_path, my_file):
        for dirpath, _, filenames in os.walk(my_path):  #
            if my_file in filenames:
                full_file_path = Path(str(os.path.join(dirpath, my_file)))  # Return full path if found
                return full_file_path
        return None  # Return None if not found

    def _mock_echo_server(self):
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
        print(f"[{self.mock_server_app}]: Loading cert + key files from: {full_path_to_cert_file}")
        context.load_cert_chain(certfile=full_path_to_cert_file,
                                keyfile=full_path_to_key_file)

        print(f"[{self.mock_server_app}]: Wrapping the 'regular' TCP/IP socket to be SSL 'secured' socket ...")
        self.server_socket = context.wrap_socket(self.server_socket,
                                                 server_side=True)  # <--- this line tells python that this is a Server and not a Client
        self.server_socket.bind((self.IP, self.PORT))
        self.server_socket.listen(1)  # Allow 1 client

        print(f"[{self.mock_server_app}] @@@ Mock server started, waiting for connection @@@ ...")
        self.client_socket, client_address = self.server_socket.accept()
        print(f"[{self.mock_server_app}]: Connection is established with client ip address: {client_address}, type: {type(self.client_socket)}")

        while True:
            try:
                data = self.client_socket.recv(1024)
                if not data:
                    print(f"[{self.mock_server_app}]: Client disconnected")
                    break
                print(f"[{self.mock_server_app}] got request from client-----> {data.decode()}")
                self.client_socket.sendall(data)
                print(f"[{self.mock_server_app}] sent echo response")
            except Exception:
                break
        self.client_socket.close()
        print(f"[{self.mock_server_app}]: Client socket - closed")
        self.server_socket.close()
        print(f"[{self.mock_server_app}]: Server socket - closed")

    def start_mock_server(self):
        """
        flag daemon means:
            daemon = False means: The main program will wait for the thread to finish before main program exits <- this is what we need
            daemon = True means: when main program finishes, all threads created by him also finish automatically & immediately
        :return:
        """
        """Start the mock server in a background thread."""
        print(f"\n[{self.mock_server_app}]: creating mock echo server thread ....")
        self.server_thread = threading.Thread(target=self._mock_echo_server,
                                              name="Mock server",
                                              daemon=True)
        print(f"\n[{self.mock_server_app}]: mock echo server thread - created")
        self.server_thread.start()
        print(f"\n[{self.mock_server_app}]: mock echo server thread - started\n")
        # Give it a moment to start, then return the server thread to the test - so test can take control over it (to kill if needed / to ask is_alive())
        time.sleep(1)
        return self.server_thread

    def is_alive(self):
        return self.server_thread.is_alive()

    def kill(self):
        if self.server_thread:
            self.server_thread.join()

"""
request.cls - refers to the test class where the fixture is used (we use it in class TestClient), not an instance of the class.
This allows you to set class-level variables that all test methods can access.
In this case, request.cls.mock_server is used to store the mock server, so that the mock server is accessible to all tests in the test class.
---------------------------
scope="class":
This means that the fixture is set up once for the entire class and is shared across all tests in that class. 
The fixture setup happens once before any test runs, and the fixture teardown happens once after all tests have completed

autouse=True:
This makes the fixture automatically used by every test in the class, 
without the need to explicitly add it as an argument to each test. Normally, 
a fixture is only invoked when it’s passed as an argument to a test function or method, but with autouse=True, it’s automatically invoked for each test
"""
@pytest.fixture()#scope="class", autouse=True)
def mock_server_fixture():
    # Part 1 - called: Fixture Setup
    print("\n\n[Fixture Setup]: Starting mock server - TEST START >>>>>>>>>>>>>>>>>>>>>>>>>>>\n")
    #if not hasattr(request.cls, 'mock_server'):
    mock_server = MockServer()#request.cls.
    mock_server.start_mock_server()
    yield
    # Part 2 - called: Fixture TearDown
    if mock_server and mock_server.is_alive():
        mock_server.kill()
    print("\n[Fixture Teardown]: Stopping mock server - Test END <<<<<<<<<<<<<<<<<<<<<<<<<")


class TestClient:
    # class data
    mock_server = None

    def test_client_sends_and_receives_same_message_single(self, mock_server_fixture):
        """Test that the client sends and receives the correct message."""
        client_obj = Client()
        client_obj.send("Hello Server")
        response = client_obj.client_socket.recv(1024).decode()
        assert response == "Hello Server"

    def test_client_sends_and_receives_multiple_messages(self, mock_server_fixture):
        """Test that the client sends and receives the correct message."""
        client_obj = Client()
        for ind in range(0,100):
            msg = f"[msg_{ind}]:Hello_Server"
            client_obj.send(msg)
            response = client_obj.client_socket.recv(1024).decode()
            assert response == msg