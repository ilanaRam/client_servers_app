import os
from pathlib import Path
import pytest
from src.client_tcp import Client
from multiprocessing import Process # < --- to simulate Server in a process to be anle to kill the server process in any moment
import socket
from typing import Final # < --- makes my types be final without ability to change their type
import ssl
import yaml
import time

class MockServer:
    def __init__(self,app_name = None):
        self.client_socket = None
        self.server_socket = None
        self.server_process = None

        self.is_server_connected = False
        self.mock_server_app: Final[str] = app_name

        self.cert_file = self._find_full_file_path(Path.cwd().parent, "ilana_cert_01.pem")
        self.key_file = self._find_full_file_path(Path.cwd().parent, "ilana_key_01.pem")
        if not self.cert_file or not self.key_file:
            raise FileExistsError
        print(f"[{self.mock_server_app}]: Loading cert file, from path: {self.cert_file}")
        print(f"[{self.mock_server_app}]: Loading key file, from path: {self.key_file}")

        full_path_to_file = self._find_full_file_path(Path.cwd().parent, "server_config.yaml")
        print(f"[{self.mock_server_app}]: Loading configuration for the server from: {full_path_to_file}")
        if not full_path_to_file:
            raise FileExistsError

        print(f"[{self.mock_server_app}]: app is executed using the next parameters: ")
        with open(full_path_to_file, "r") as yaml_file:
            config = yaml.safe_load(yaml_file)

        self.IP: Final[str] = config["server"]["ip_address"]  # also possible to do: socket.gethostbyname(socket.gethostname()) if not ip else ip  # <---- this way we determine the local host address, this way -> we set it hard codded: "127.0.0.1" if not ip else ip
        print(f"[{self.mock_server_app}]: IP: {self.IP}")
        self.PORT: Final[int] = config["server"]["port"]  # also possible to do: 8820 if not port else port
        print(f"[{self.mock_server_app}]: PORT: {self.PORT}")
        self.MAX_DATA_SIZE = config["server"]["max_data_size"]
        print(f"[{self.mock_server_app}]: Max data size: {self.MAX_DATA_SIZE}")

    def _find_full_file_path(self, my_path, my_file):
        for dirpath, _, filenames in os.walk(my_path):  #
            if my_file in filenames:
                full_file_path = Path(str(os.path.join(dirpath, my_file)))  # Return full path if found
                return full_file_path
        return None  # Return None if not found

    def _always_living_mock_echo_server(self):
        print(f"[{self.mock_server_app}] @@@ Echo Mock Server started, waiting for Client connection @@@ ...")
        self.client_socket, client_address = self.server_socket.accept()
        self.is_server_connected = True
        print(f"[{self.mock_server_app}]: Client connection is established with client ip address: {client_address}, type: {type(self.client_socket)}")

        print(f"[{self.mock_server_app}]: Server started receiving and resending back ...")
        while True:
            try:
                data = self.client_socket.recv(1024)
                if not data:
                    print(f"[{self.mock_server_app}]: Detected that Client was gracefully disconnected")
                    break
                print(f"[{self.mock_server_app}] got request from client-----> {data.decode()}")
                self.client_socket.sendall(data)
                print(f"[{self.mock_server_app}] sent echo response")
            except Exception:
                print(f"[{self.mock_server_app}]: seems like Client crashed")
                break

        self.client_socket.close()
        print(f"[{self.mock_server_app}]: Client socket - closed")
        self.server_socket.close()
        print(f"[{self.mock_server_app}]: Server socket - closed")

    def _mock_echo_server_disconnects_after_connection(self):
        print(f"[{self.mock_server_app}] @@@ Echo Mock Server started, waiting for Client connection @@@ ...")
        self.client_socket, client_address = self.server_socket.accept()
        self.is_server_connected = True
        print(f"[{self.mock_server_app}]: Client connection is established with client ip address: {client_address}, type: {type(self.client_socket)}")
        print(f"[{self.mock_server_app}]: Server will stay connected for 4 sec and terminate")
        time.sleep(4)
        print(f"[{self.mock_server_app}]: Server will terminate now ...")
        self.client_socket.close()
        print(f"[{self.mock_server_app}]: Client socket - closed")
        self.server_socket.close()
        print(f"[{self.mock_server_app}]: Server socket - closed")
        self.is_server_connected = False

    def _mock_echo_server_disconnects_after_resend_back(self):
        print(f"[{self.mock_server_app}] @@@ Echo Mock Server started, waiting for Client connection @@@ ...")
        self.client_socket, client_address = self.server_socket.accept()
        print(f"[{self.mock_server_app}]: Client connection is established with client ip address: {client_address}, type: {type(self.client_socket)}")

        print(f"[{self.mock_server_app}]: Server started receiving and resending back ...")
        ind = 0
        while ind <= 10:
            try:
                print(f"[{self.mock_server_app}]: waiting to receive msg: {ind}")
                data = self.client_socket.recv(1024)
                if not data:
                    print(f"[{self.mock_server_app}]: Client disconnected")
                    break
                print(f"[{self.mock_server_app}] received msg: -----> {data.decode()}")
                self.client_socket.sendall(data)
                print(f"[{self.mock_server_app}] sent echo response")
                ind += 1
            except Exception:
                break
        self.client_socket.close()
        print(f"[{self.mock_server_app}]: Client socket - closed")
        self.server_socket.close()
        print(f"[{self.mock_server_app}]: Server socket - closed")

    def prepare_echo_mock_server_socket(self, mock_server_app, ip, port, cert_file, key_file):

        print(f"[{mock_server_app}]: Creating mock echo server socket ...")
        server_socket = socket.socket(socket.AF_INET,
                                      socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        print(f"[{mock_server_app}]: Creating SSL context  for my echo auto server ...")
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        # load certificate + key (certificate for authentication with Client, keys for encryption messages)
        print(f"[{mock_server_app}]: Load Authentication certificate and encryption keys, for secure connection ...")

        print(f"[{mock_server_app}]: Loading cert + key files from: {cert_file}")
        context.load_cert_chain(certfile=cert_file,
                                keyfile=key_file)

        print(f"[{mock_server_app}]: Wrapping the 'regular' TCP/IP socket to be SSL 'secured' socket ...")
        server_socket = context.wrap_socket(server_socket,
                                            server_side=True)  # <--- this line tells python that this is a Server and not a Client
        server_socket.bind((ip,port))
        server_socket.listen(1)  # Allow 1 client
        return server_socket

    def mock_echo_server_crashes_after_connection(self,
                                                  mock_server_app, ip, port, cert_file, key_file):

        self.server_socket = self.prepare_echo_mock_server_socket(mock_server_app=mock_server_app,
                                                                  ip=ip, port=port, cert_file=cert_file, key_file=key_file)

        print(f"[{mock_server_app}] @@@ Echo Mock Server started, waiting for Client connection @@@ ...")
        client_socket, client_address = self.server_socket.accept()

        print(f"[{mock_server_app}]: Client connection is established with client ip address: {client_address}, type: {type(client_socket)}")
        print(f"[{mock_server_app}]: Server will stay connected for 4 sec and terminate")
        time.sleep(4)
        print(f"[{mock_server_app}]: Server thread finishes without closing client_socket & server_socket ...")

    def start_mock_server_crashes_after_connection(self, mock_server_app, ip, port, cert_file, key_file):
        print(f"\n[{mock_server_app}]: creating 'Mock_Server' process ....")
        self.server_process = Process(target=self.mock_echo_server_crashes_after_connection,
                                 name='Mock_Server',
                                 args=((mock_server_app, ip, port, cert_file, key_file)))
        self.server_process.start()
        print(f"\n[{mock_server_app}]: mock echo server process - started\n")
        # Give it a moment to process to start, then return the server process to the test - so test can take control over it (to kill if needed / to ask is_alive())
        time.sleep(2)
        return self.server_process

    # def start_always_living_mock_server(self):
    #     """
    #     flag daemon means:
    #         daemon = False means: The main program will wait for the thread to finish before main program exits <- this is what we need
    #         daemon = True means: when main program finishes, all threads created by him also finish automatically & immediately
    #     :return:
    #     """
    #     """Start the Always_Living_Mock_Server in a background thread."""
    #     self._prepare_echo_mock_server()
    #
    #     print(f"\n[{self.mock_server_app}]: creating 'Always_Living_Mock_Server' thread ....")
    #     self.server_thread = threading.Thread(target=self._always_living_mock_echo_server,
    #                                           name="Always_Living_Mock_Server",
    #                                           daemon=True)
    #     print(f"\n[{self.mock_server_app}]: mock echo server thread - created")
    #     self.server_thread.start()
    #     print(f"\n[{self.mock_server_app}]: mock echo server thread - is running\n")
    #     # Give it a moment to start, then return the server thread to the test - so test can take control over it (to kill if needed / to ask is_alive())
    #     time.sleep(1)
    #     return self.server_thread
    #
    # def start_mock_server_disconnects_after_connection(self):
    #     """
    #     flag daemon means:
    #         daemon = False means: The main program will wait for the thread to finish before main program exits <- this is what we need
    #         daemon = True means: when main program finishes, all threads created by him also finish automatically & immediately
    #     :return:
    #     """
    #     """Start the Mock_Server_failed_right_after_creation in a background thread."""
    #     self._prepare_echo_mock_server()
    #
    #     print(f"\n[{self.mock_server_app}]: creating 'Always_Living_Mock_Server' thread ....")
    #     self.server_thread = threading.Thread(target=self._mock_echo_server_disconnects_after_connection,
    #                                           name="Always_Living_Mock_Server",
    #                                           daemon=True)
    #     print(f"\n[{self.mock_server_app}]: mock echo server thread - created")
    #     self.server_thread.start()
    #     print(f"\n[{self.mock_server_app}]: mock echo server thread - started\n")
    #     # Give it a moment to start, then return the server thread to the test - so test can take control over it (to kill if needed / to ask is_alive())
    #     time.sleep(1)
    #     return self.server_thread



    # def start_mock_server_disconnects_after_resend_back(self):
    #     """
    #     flag daemon means:
    #         daemon = False means: The main program will wait for the thread to finish before main program exits <- this is what we need
    #         daemon = True means: when main program finishes, all threads created by him also finish automatically & immediately
    #     :return:
    #     """
    #     """Start the mock_server_disconnects_during_session_app in a background thread."""
    #     self._prepare_echo_mock_server()
    #
    #     print(f"\n[{self.mock_server_app}]: creating 'Mock_Server_fails_during_session' thread ....")
    #     self.server_thread = threading.Thread(target=self._mock_echo_server_disconnects_after_resend_back,
    #                                           name="Mock_Server_fails_during_session",
    #                                           daemon=True)
    #     print(f"\n[{self.mock_server_app}]: mock echo server thread - created")
    #     self.server_thread.start()
    #     print(f"\n[{self.mock_server_app}]: mock echo server thread - started\n")
    #     # Give it a moment to start, then return the server thread to the test - so test can take control over it (to kill if needed / to ask is_alive())
    #     time.sleep(1)
    #     return self.server_thread



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
# @pytest.fixture()#scope="class", autouse=True)
# def always_living_mock_server_fixture():
#     # Part 1 - called: Fixture Setup
#     print("\n\n[Fixture Setup]: Starting mock server - TEST START >>>>>>>>>>>>>>>>>>>>>>>>>>>\n")
#     mock_server = MockServer(app_name="ALWAYS_LIVING_MOCK_SERVER")
#     mock_server.start_always_living_mock_server()
#     yield
#     # Part 2 - called: Fixture TearDown
#     if mock_server and mock_server.is_alive():
#         mock_server.kill()
#     print("\n[Fixture Teardown]: Stopping mock server - Test END <<<<<<<<<<<<<<<<<<<<<<<<<")
#
# @pytest.fixture()
# def mock_server_disconnects_right_after_connection_fixture():
#     # Part 1 - called: Fixture Setup
#     print("\n\n[Fixture Setup]: Starting mock server - TEST START >>>>>>>>>>>>>>>>>>>>>>>>>>>\n")
#     mock_server = MockServer(app_name="MOCK_SERVER_DISCONNECTS_AFTER_CONNECTION")
#     mock_server.start_mock_server_disconnects_after_connection()
#     yield
#     # Part 2 - called: Fixture TearDown
#     if mock_server and mock_server.is_alive():
#         mock_server.kill()
#     print("\n[Fixture Teardown]: Stopping mock server - Test END <<<<<<<<<<<<<<<<<<<<<<<<<")
#
# @pytest.fixture()
# def mock_server_crashes_right_after_connection_fixture():
#     # Part 1 - called: Fixture Setup
#     print("\n\n[Fixture Setup]: Starting mock server - TEST START >>>>>>>>>>>>>>>>>>>>>>>>>>>\n")
#     mock_server = MockServer(app_name="MOCK_SERVER_CRASHES_AFTER_CONNECTION")
#     mock_server.start_mock_server_crashes_after_connection()
#     yield
#     # Part 2 - called: Fixture TearDown
#     if mock_server and mock_server.is_alive():
#         mock_server.kill()
#     print("\n[Fixture Teardown]: Stopping mock server - Test END <<<<<<<<<<<<<<<<<<<<<<<<<")
#
# @pytest.fixture()
# def mock_server_fails_after_resend_back():
#     # Part 1 - called: Fixture Setup
#     print("\n\n[Fixture Setup]: Starting mock server - TEST START >>>>>>>>>>>>>>>>>>>>>>>>>>>\n")
#     mock_server = MockServer(app_name="MOCK_SERVER_FAILS_AFTER_RESEND_BACK")
#     mock_server.start_mock_server_disconnects_after_resend_back()
#     yield
#     # Part 2 - called: Fixture TearDown
#     if mock_server and mock_server.is_alive():
#         mock_server.kill()
#     print("\n[Fixture Teardown]: Stopping mock server - Test END <<<<<<<<<<<<<<<<<<<<<<<<<")

class TestClient:

    def test_client_server_crashes_after_connection(self):#, mock_server_crashes_right_after_connection_fixture):
        """
        FIXED
        This test checks that when Server is terminated (closed / crashed without closing sockets correctly) after connection with Client but before client send msg, can be handled ok by client
        What should happen when Server process terminates? OS will delete the socket obj, so when Client will try to send - this send should fail -> this is what we check here
        No message could be sent
        """
        res = None
        app_name = "MOCK_SERVER_TERMINATES_AFTER_CONNECTION"
        # prepare mock server params
        mock_server = MockServer(app_name=app_name)
        # create mock server process (using mock server params), process will be created and will wait for a connection from Client side
        # once Client will connect server will be terminated

        # this func is not part of the
        mock_server_process = mock_server.start_mock_server_crashes_after_connection(mock_server_app=app_name,
                                                                                       ip=mock_server.IP,
                                                                                       port=mock_server.PORT,
                                                                                       cert_file=mock_server.cert_file,
                                                                                       key_file=mock_server.key_file) # <--- here thread will wait till Client connects
        # connect client side
        client_obj = Client()
        mock_server_process.terminate()
        # wait for server termination - by using join() we will be sure server terminated
        mock_server_process.join()
        # try send messages from Client -> Server see no messages could be received by Server
        results_list = []
        for ind in range(0, 5):
            res = client_obj.send("Hello_Server")
            print(f"[CLIENT_TEST]: res: {res}")
            results_list.append(res)
            res = client_obj._receive()
            print(f"[CLIENT_TEST]: res: {res}")
            results_list.append(res)
        else:
            print(f"[CLIENT_TEST]: Mock Server is terminated after connection with Client and before Client could send first msg")
        print(f"[CLIENT_TEST]: all the attempts to send msg from Client -> Mock server, expected to be resulted with False: \n{results_list}")
        assert all(not bool(item) for item in results_list)

    # def test_client_single_message_send(self, always_living_mock_server_fixture):
    #     """Test that the client sends and receives the correct message."""
    #     client_obj = Client()
    #     client_obj.send("Hello Server")
    #     response = client_obj._receive()
    #     assert response
    #
    # def test_client_multiple_messages_send(self, always_living_mock_server_fixture):
    #     """Test that the client sends and receives the correct message."""
    #     client_obj = Client()
    #     for ind in range(0,100):
    #         msg = f"[msg_{ind}]:Hello_Server"
    #         client_obj.send(msg)
    #         response = client_obj._receive()
    #         assert response
    #
    # def test_client_server_disconnects_after_connection(self, mock_server_disconnects_right_after_connection_fixture):
    #     """
    #     FIXED
    #     Test that the client can recognize that Server 'disconnected' (not crashed)
    #     4 secs after connection. While Client started sending right away -> it means there is a chance that 'send' operation from Client can succeed
    #     while message will never be received at the Server side as mock server did not even call receive() method
    #     """
    #     res = None
    #     client_obj = Client()
    #     for ind in range(0,5):
    #         res = client_obj.send("Hello_Server")
    #         print(f"[CLIENT_TEST]: res: {res}")
    #         res = client_obj._receive()
    #         print(f"[CLIENT_TEST]: res: {res}")
    #     print(f"[CLIENT_TEST]: Client is expected to fail after very few sends, res should be False, res is: {res}")
    #     assert not res
    #
    # def test_client_server_fails_after_resend_back(self, mock_server_fails_after_resend_back):
    #     """
    #     FIXED
    #     Test that the client can recognize that Server 'disconnected' (not crashed)
    #     at some point during send and receive. After server disconnects sending of the messages should fail
    #     """
    #     client_obj = Client()
    #     res = None
    #     ind = 0
    #     for ind in range(0,100):
    #         res = client_obj.send(f"[msg_{ind}]:Hello_Server")
    #         print(f"[CLIENT_TEST] send() returned with: {res}")
    #         res = client_obj._receive()
    #         print(f"[CLIENT_TEST] _receive() returned with: {res}")
    #         if not res:
    #             break
    #     else:
    #         raise Exception("f[CLIENT_TEST] ERROR: all messages will pass")
    #     assert not res and ind == 11
    #     print(f"[CLIENT_TEST] Test expected that only ~11 first messages will be sent & responded (after it Server disconnected)")



