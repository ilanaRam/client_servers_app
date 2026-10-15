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

# I import the real multi client server since I wish to check if and when single Client send 'q' and disconnects the server disconnects too.
from src.multi_client_by_select_server_tcp import Multi_Clients_Server as MultiClientServer


class MockServer:
    def __init__(self,app_name = "MockServer"):
        self.client_socket = None
        self.server_socket = None
        self.server_process = None

        self.is_server_connected = False
        self.app: Final[str] = app_name

        self.cert_file = self._find_full_file_path(Path.cwd().parent, "ilana_cert_01.pem")
        self.key_file = self._find_full_file_path(Path.cwd().parent, "ilana_key_01.pem")
        if not self.cert_file or not self.key_file:
            raise FileExistsError
        print(f"[{self.app}]: Loading cert file, from path: {self.cert_file}")
        print(f"[{self.app}]: Loading key file, from path: {self.key_file}")

        full_path_to_file = self._find_full_file_path(Path.cwd().parent, "server_config.yaml")
        print(f"[{self.app}]: Loading configuration for the server from: {full_path_to_file}")
        if not full_path_to_file:
            raise FileExistsError

        print(f"[{self.app}]: app is executed using the next parameters: ")
        with open(full_path_to_file, "r") as yaml_file:
            config = yaml.safe_load(yaml_file)

        self.IP: Final[str] = config["server"]["ip_address"]  # also possible to do: socket.gethostbyname(socket.gethostname()) if not ip else ip  # <---- this way we determine the local host address, this way -> we set it hard codded: "127.0.0.1" if not ip else ip
        print(f"[{self.app}]: IP: {self.IP}")
        self.PORT: Final[int] = config["server"]["port"]  # also possible to do: 8820 if not port else port
        print(f"[{self.app}]: PORT: {self.PORT}")
        self.MAX_DATA_SIZE = config["server"]["max_data_size"]
        print(f"[{self.app}]: Max data size: {self.MAX_DATA_SIZE}")

    def _find_full_file_path(self, my_path, my_file):
        for dirpath, _, filenames in os.walk(my_path):  #
            if my_file in filenames:
                full_file_path = Path(str(os.path.join(dirpath, my_file)))  # Return full path if found
                return full_file_path
        return None  # Return None if not found


    def _mock_echo_server_disconnects_after_connection(self):
        print(f"[{self.app}] @@@ Echo Mock Server started, waiting for Client connection @@@ ...")
        self.client_socket, client_address = self.server_socket.accept()
        self.is_server_connected = True
        print(f"[{self.app}]: Client connection is established with client ip address: {client_address}, type: {type(self.client_socket)}")
        print(f"[{self.app}]: Server will stay connected for 4 sec and terminate")
        time.sleep(4)
        print(f"[{self.app}]: Server will terminate now ...")
        self.client_socket.close()
        print(f"[{self.app}]: Client socket - closed")
        self.server_socket.close()
        print(f"[{self.app}]: Server socket - closed")
        self.is_server_connected = False

    def _mock_echo_server_disconnects_after_resend_back(self):
        print(f"[{self.app}] @@@ Echo Mock Server started, waiting for Client connection @@@ ...")
        self.client_socket, client_address = self.server_socket.accept()
        print(f"[{self.app}]: Client connection is established with client ip address: {client_address}, type: {type(self.client_socket)}")

        print(f"[{self.app}]: Server started receiving and resending back ...")
        ind = 0
        while ind <= 10:
            try:
                print(f"[{self.app}]: waiting to receive msg: {ind}")
                data = self.client_socket.recv(1024)
                if not data:
                    print(f"[{self.app}]: Client disconnected")
                    break
                print(f"[{self.app}] received msg: -----> {data.decode()}")
                self.client_socket.sendall(data)
                print(f"[{self.app}] sent echo response")
                ind += 1
            except Exception as ee:
                print(f"[{self.app}] error occurred: {ee}")
                break
        self.client_socket.close()
        print(f"[{self.app}]: Client socket - closed")
        self.server_socket.close()
        print(f"[{self.app}]: Server socket - closed")

    def prepare_echo_mock_server_socket(self, ip, port, cert_file, key_file):
        """
        Shared helper task actually builds the TLS socket (create socket → wrap with SSL → bind → listen).
        :param mock_server_app:
        :param ip:
        :param port:
        :param cert_file:
        :param key_file:
        :return:
        """

        print(f"[{self.app}]: Creating mock echo server socket ...")
        server_socket = socket.socket(socket.AF_INET,
                                      socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        print(f"[{self.app}]: Creating SSL context  for my echo auto server ...")
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        # load certificate + key (certificate for authentication with Client, keys for encryption messages)
        print(f"[{self.app}]: Load Authentication certificate and encryption keys, for secure connection ...")

        print(f"[{self.app}]: Loading cert + key files from: {cert_file}")
        context.load_cert_chain(certfile=cert_file,
                                keyfile=key_file)

        print(f"[{self.app}]: Wrapping the 'regular' TCP/IP socket to be SSL 'secured' socket ...")
        server_socket = context.wrap_socket(server_socket,
                                            server_side=True)  # <--- this line tells python that this is a Server and not a Client
        server_socket.bind((ip,port))
        server_socket.listen(1)  # Allow 1 client
        return server_socket

    def mock_echo_server_crashes_after_connection(self,ip, port, cert_file, key_file):

        self.server_socket = self.prepare_echo_mock_server_socket(ip=ip, port=port, cert_file=cert_file, key_file=key_file)
        print(f"[{self.app}] @@@ Echo Mock Server started, waiting for Client connection @@@ ...")
        self.client_socket, client_address = self.server_socket.accept()
        print(f"[{self.app}]: Client connection is established with client ip address: {client_address}, type: {type(self.client_socket)}")
        print(f"[{self.app}]: Server will stay connected for 4 sec and terminate")
        time.sleep(4)
        print(f"[{self.app}]: Server thread finishes without closing client_socket & server_socket ...")

    def mock_echo_server_send_receive_session(self, ip, port, cert_file, key_file):
        self.server_socket = self.prepare_echo_mock_server_socket(ip=ip, port=port, cert_file=cert_file, key_file=key_file)
        print(f"[{self.app}] @@@ Echo Mock Server started, waiting for Client connection @@@ ...")
        self.client_socket, client_address = self.server_socket.accept()
        print(f"[{self.app}]: Client connection is established with client ip address: {client_address}, type: {type(self.client_socket)}")

        print(f"[{self.app}]: Server started receiving and resending back ...")
        ind = 0
        while True:
            try:
                print(f"[{self.app}]: waiting to receive msg: {ind}")
                data = self.client_socket.recv(1024)
                if not data:
                    print(f"[{self.app}]: Client disconnected")
                    break
                print(f"[{self.app}] received msg: -----> {data.decode()}")
                self.client_socket.sendall(data)
                print(f"[{self.app}] sent echo response")
                ind += 1
            except Exception as ee:
                print(f"[{self.app}] error occurred: {ee}")
                break

    def mock_server_crashes_after_connection(self, ip, port, cert_file, key_file):
        print(f"\n[{self.app}]: creating 'Mock_Server' process ....")
        self.server_process = Process(target=self.mock_echo_server_crashes_after_connection,
                                      name='Mock_Server',
                                      args=((ip, port, cert_file, key_file)))
        self.server_process.start()
        print(f"\n[{self.app}]: mock echo server process - started\n")
        # Give it a moment to process to start, then return the server process to the test - so test can take control over it (to kill if needed / to ask is_alive())
        time.sleep(2)
        return self.server_process

    def mock_server_send_receive_session(self, ip, port, cert_file, key_file):
        print(f"\n[{self.app}]: creating 'Mock_Server' process ....")
        self.server_process = Process(target=self.mock_echo_server_send_receive_session,
                                      name='Mock_Server',
                                      args=((ip, port, cert_file, key_file)))
        self.server_process.start()
        print(f"\n[{self.app}]: mock echo server process - started\n")
        # Give it a moment to process to start, then return the server process to the test - so test can take control over it (to kill if needed / to ask is_alive())
        time.sleep(2)
        return self.server_process


def _start_multi_client_server(delay_value):
    """Process target: runs the real multi-client Server until it shuts itself down."""
    time.sleep(delay_value)
    multi_clients_server_obj = MultiClientServer()
    multi_clients_server_obj.start()



class TestClient:
    # since in pytest - we cannot use constructor (no test will be collected) we can use class attribute
    app: Final[str] = "ClientTest"

    def test_client_where_server_crashes_after_connection(self):
        """
        FIXED
        This test checks that when Server is terminated (closed / crashed without closing sockets correctly) after connection with Client but before client send msg,
        can be handled ok by client
        What should happen when Server process terminates? OS will delete the socket obj, so when Client will try to send - this send should fail -> this is what we check here
        No message could be sent
        """
        res = None
        # prepare mock server params only (not the mock server yet)
        mock_server = MockServer()
        # create mock server process (using mock server params), process will be created and will wait for a connection from Client side
        # once Client will connect server will be terminated

        # this func is not part of the
        mock_server_process = mock_server.mock_server_crashes_after_connection(ip=mock_server.IP,
                                                                               port=mock_server.PORT,
                                                                               cert_file=mock_server.cert_file,
                                                                               key_file=mock_server.key_file) # <--- here thread will wait till Client connects        # connect client side
        # create client and connect to a server
        client_obj = Client()
        mock_server_process.terminate()
        # wait for server termination - by using join() we will be sure server terminated
        mock_server_process.join()
        # try send messages from Client -> Server see no messages could be received by Server
        results_list = []
        for ind in range(0, 5):
            res = client_obj.send(f"Hello_Server_{ind}")
            print(f"[{self.app}]: res: {res}")
            results_list.append(res)
            res = client_obj._receive()
            print(f"[{self.app}]: res: {res}")
            results_list.append(res)
        else: # else to for loop = get to else only if loop was not broken - completed
            print(f"[{self.app}]: Mock Server is terminated after connection with Client and before Client could send first msg")
        print(f"[{self.app}]: all the attempts to send msg from Client -> Mock server, expected to be resulted with False: \n{results_list}")
        assert all(not bool(item) for item in results_list)

    def test_client_where_server_crashes_during_send_receive_session(self):
        res = None
        # prepare mock server params
        mock_server = MockServer()
        # create mock server process (using mock server params), process will be created and will wait for a connection from Client side
        # once Client will connect server will be terminated

        mock_server_process = mock_server.mock_server_send_receive_session(ip=mock_server.IP,
                                                                           port=mock_server.PORT,
                                                                           cert_file=mock_server.cert_file,
                                                                           key_file=mock_server.key_file) # <--- here thread will wait till Client connects        # connect client side
        client_obj = Client()
        # try send messages from Client -> Server see no messages could be received by Server
        results_list = []
        for ind in range(0, 15):
            if ind == 5:
                mock_server_process.terminate()
                # wait for server termination - by using join() we will be sure server terminated
                mock_server_process.join()
            res = client_obj.send("Hello_Server")
            print(f"[{self.app}]: res: {res}")
            results_list.append(res)
            res = client_obj._receive()
            print(f"[{self.app}]: res: {res}")
            results_list.append(res)
        else:
            print(f"[{self.app}]: Mock Server is terminated after connection with Client and before Client could send first msg")
        print(f"[{self.app}]: failed attempts to send msg from Client -> Mock server: {results_list.count(False)}")
        assert results_list.count(False) != 0

    def test_client_single_message_send(self):
        """Test that the client sends and receives the correct message."""
        # prepare mock server params
        mock_server = MockServer()

        # create mock server process - it will accept one client and echo messages back, forever
        mock_server_process = mock_server.mock_server_send_receive_session(ip=mock_server.IP,
                                                                           port=mock_server.PORT,
                                                                           cert_file=mock_server.cert_file,
                                                                           key_file=mock_server.key_file)
        try:
            client_obj = Client()
            client_obj.send("Hello Server")
            response = client_obj._receive()
        finally:
            # stop the mock server no matter if client failed to send/receive - this way we make sure the mock server process is stopped even if try section raised exception.
            mock_server_process.terminate()
            mock_server_process.join()
        assert response

    def test_client_gives_up_after_max_retries(self):
        """
        Test that when no server is listening at all, the Client exhausts every
        connection attempt (max_retries) and then gives up (exit(1)) instead of
        hanging or retrying forever.

        No mock server is started here on purpose - nothing is listening on the
        configured port, so every attempt fails fast with ConnectionRefusedError.

        retry delay = 2, max_retries:  10, test shell run not more than 20 sec
        """
        print(f"[{self.app}]: Test will run client that will try to connect while there is NO MOCK server at all. test will check that client gives up after retries")

        start_time = time.time()

        # with is a context loop, what makes this to be a loop, the looping operation inside the with (read file line by line, listening to the mic, ..) once the inner operation expected to fail
        # the context manager that catches the exit(1) (exit(1) causes a system to generate System_exit signal)
        # Now we know to catch this error signal
        with pytest.raises(SystemExit) as exc_info:
            # since the server is not running Client() is expected to generate a system error signal called: SystemExit,
            # if this signal will be generated it will be caught it by with context manager: pytest.raises
            Client()
        elapsed_time = time.time() - start_time
        print(f"[{self.app}]: Client gave up after {elapsed_time:.1f} seconds")
        # if assert is caught the exc_info.value is set with != 1
        assert exc_info.value.code == 1

    def test_multi_client_server_shuts_down_after_last_client_sends_q(self):
        """
        Test that the REAL multi-client server shuts itself down once the single (last) connected client disconnects by sending 'q'.
        This test will check ability of the server to handle with empty msg or message with 'q'
        For this test I imported the real multi client server since I wish to check if and when single Client send 'q' and disconnects the server disconnects too.
        Test does:
        Single Client connects to server -> starts_sending messages -> send q to quit. Client quites correctly, also Server quites correctly
        exit() / sys.exit() - are both raise SystemExit - they cause return not from a function but from entire program
        """
        print(f"[{self.app}]: Test does: creates client -> connects server -> sends q quits to quit the connection")

        print(f"[{self.app}]: Starting real multi client server")
        multi_client_server = Process(target=_start_multi_client_server,
                                      args=((0,)),
                                      name='MULTI_CLIENT_SERVER')
        multi_client_server.start()

        print(f"[{self.app}]: Starting single client to run and send messages to selver")
        msg = "Hello Server - I am single client"
        try:
            client_obj = Client()
            client_obj.send(msg)
            res = client_obj._receive()
            assert res

            client_obj.send("How are you Server ?")
            res = client_obj._receive()
            assert res

            print(f"[{self.app}]: The single client is about to quit .. by sending 'q' to server")
            client_obj.send("q")
            # join:
            # It is always blocking operation - that waits for process to finish. Code will not keep running till it is blocked on join
            # if we use timeout (10 sec) code will stack to wait only 10 sec and then it gives up and keep running
            # if we dont use timeout - code will wait till process finishes (and if process stack the code will stack waiting forever)
            multi_client_server.join(timeout=10)
            # lets take most resent indicator right here
            flag = multi_client_server.is_alive() # is_alive() = true only if server is running
            assert not flag # this is the end of test: Flag = True test fails, Flag = False test passed, BUT the finally block will happen any way
        finally:
            # here we do operations we need to do either way (either server finished ok or any one crashed
            # Close server
            if multi_client_server.is_alive():
                multi_client_server.terminate()
                # termination takes time so we cannot to exit right away we need to wait - therefore we need join
                multi_client_server.join()


    def test_multi_client_server_shuts_down_after_all_clients_are_quit(self):
        """
        Test that the REAL multi-client server shuts itself down once the single (last) connected client disconnects by sending 'q'.
        This test will check ability of the server to handle with empty msg or message with 'q'
        For this test I imported the real multi client server since I wish to check if and when single Client send 'q' and disconnects the server disconnects too.
        """
        print(f"[{self.app}]: Test does: client1 -> connects server, client2 -> connect server. Client1 quits while server keeps alive, client2 quits server is terminated")

        print(f"[{self.app}]: Starting real multi client server")
        multi_client_server = Process(target=_start_multi_client_server,
                                      args=((0,)),
                                      name='MULTI_CLIENT_SERVER')
        multi_client_server.start()

        print(f"[{self.app}]: Connecting client1 ...")

        msg = "Hello Server - I am client: "
        try:
            client_1 = Client()
            client_1.send(msg + "1")
            res = client_1._receive()
            assert res

            client_2 = Client()
            client_2.send(msg + "2")
            res = client_2._receive()
            assert res

            print(f"[{self.app}]: The client_1 is about to quit .. by sending 'q' to server")
            client_1.send("q")
            multi_client_server.join(timeout=10)
            # lets take most resent indicator right here
            client_1_flag = multi_client_server.is_alive()
            assert client_1_flag

            print(f"[{self.app}]: The client_2 is about to quit .. by sending 'q' to server")
            client_2.send("q")
            multi_client_server.join(timeout=10)
            # lets take most resent indicator right here
            client_2_flag = multi_client_server.is_alive()
            assert not client_2_flag
        finally:
            # here we do operations we need to do either way (either server finished ok or any one crashed
            # Close server
            if multi_client_server.is_alive():
                multi_client_server.terminate()
                # termination takes time so we cannot to exit right away we need to wait - therefore we need join
                multi_client_server.join()

    def test_client_start_client_server_yet_running(self):
        """
        Client starts first - trying to connect not existing server, then server starts
        """
        print(f"[{self.app}]: Test does: starts client while server yet running")

        delay_before_server_starts = 15
        print(f"[{self.app}]: Starting real multi client server, will start running BUT after delay: {delay_before_server_starts}")
        multi_client_server = Process(target=_start_multi_client_server,
                                      name='MULTI_CLIENT_SERVER',
                                      args=((delay_before_server_starts,)))
        multi_client_server.start()

        print(f"[{self.app}]: Starting client (server should not running till now - due to delay")
        msg = "Hello Server - I am single client"
        try:
            client_obj = Client() # constructor will start a blocking loop in which it will try to connect N times the server till eventual connection
            res_send = client_obj.send(msg)
            res_receive = client_obj._receive()
            assert res_send
            assert res_receive

            print(f"[{self.app}]: The single client is about to quit .. by sending 'q' to server")
            client_obj.send("q")
            # join:
            # It is always blocking operation - that waits for process to finish. Code will not keep running till it is blocked on join
            # if we use timeout (10 sec) code will stack to wait only 10 sec and then it gives up and keep running
            # if we dont use timeout - code will wait till process finishes (and if process stack the code will stack waiting forever)
            multi_client_server.join(timeout=10)
            # lets take most resent indicator right here
            flag = multi_client_server.is_alive() # is_alive() = true only if server is running
            assert not flag # this is the end of test: Flag = True test fails, Flag = False test passed, BUT the finally block will happen any way
        finally:
            # here we do operations we need to do either way (either server finished ok or any one crashed
            # Close server
            if multi_client_server.is_alive():
                multi_client_server.terminate()
                # termination takes time so we cannot to exit right away we need to wait - therefore we need join
                multi_client_server.join()


