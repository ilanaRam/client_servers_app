#import multiprocessing
from threading import Thread
import queue
import socket
import yaml
from typing import Final # makes my types be final without ability to change their type
import ssl
import certs


class Server:
    ############################################################################################
    # Server SOCKET:
    # create socket (of the type: ip socket, using TCP protocol)
    # bind (to its ip and port)
    # listen (put server socket into listen state)
    # accept (blocking wait for Client connection)
    # recv (blocking wait for Client data) -> return answer
    ############################################################################################

    def __init__(self):
        self.app: Final[str] = "SERVER"
        # self.ip: Final[str] = "127.0.0.1" if not ip else ip
        # self.port: Final[int] = 8820 if not port else port

        self.MAX_CONNECTIONS: Final[int] = 1
        self.client_socket = None
        self.server_socket = None
        self.client_messages_queue = queue.Queue() # this Q was created in context of the Server obj, therefore will leave also after thread will finish
        self.connection_store = {}                 # multiprocessing.Queue() <-- this is good when we used processes and not threads

        ip, port, max_data_size = self.init()
        print(f"[{self.app}]: app is executed using the next parameters: ")
        self.IP: Final[str] = ip # also possible to do: socket.gethostbyname(socket.gethostname()) if not ip else ip  # <---- this way we determine the local host address, this way -> we set it hard codded: "127.0.0.1" if not ip else ip
        print(f"[{self.app}]: IP: {self.IP}")

        self.PORT: Final[int] = port # also possible to do: 8820 if not port else port
        print(f"[{self.app}]: PORT: {self.PORT}")

        self.MAX_DATA_SIZE = max_data_size
        print(f"[{self.app}]: Max data size: {self.MAX_DATA_SIZE}")

    def init(self):
        with open("server_config.yaml", "r") as yaml_file:
            config = yaml.safe_load(yaml_file)
            return config["server"]["ip_address"],\
                   config["server"]["port"], \
                   config["server"]["max_data_size"]

    def start(self):
        """
        Start the server, will create 2 process:
        1. that listen to the socket + receives the messages from a client and stores in the queue
        2. that listens on the queue to the new message, retrieve and print it + add to SQL DB
        :return: None
        """
        # 1. Create a socket object
        print(f"\n\n[{self.app}]: Creating the 'regular' socket ...")
        self.server_socket = socket.socket(socket.AF_INET,
                                           socket.SOCK_STREAM) # use protocol: TCP

        # 2. prepare secure context - setting up all the rules for secure communication
        # It helps Python know how to handle encryption (TLS/SSL) for the server or client
        # ssl.Purpose.CLIENT_AUTH tells python - hi I am server, and i wish to communicate securely with client/s
        print(f"[{self.app}]: Creating the secured SSL context (set of rules for secure connection) ...")
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        # load certificate + key (certificate for authentication with Client, keys for encryption messages)
        print(f"[{self.app}]: Load Authentication certificate and encryption keys, for secure connection ...")
        context.load_cert_chain(certfile="certs/ilana_cert_01.pem",
                                keyfile="certs/ilana_key_01.pem")

        # 3. wrap regular server socket with SSL - from this moment all operations with socket, such as: Bind(), Listen(), Accept() wil be done with secured Server socket
        # wrapping means => putting message in secured envelope. All the data sent/received through the socket is authenticated and encrypted
        print(f"[{self.app}]: Wrapping the 'regular' socket to be SSL 'secured' socket ...")
        self.server_socket = context.wrap_socket(self.server_socket,
                                                 server_side=True) # <--- this line tells python that this is a Server and not a Client

        # 4. Bind the socket (secured socket) to an address and port
        self.server_socket.bind((self.IP, self.PORT))

        # 5. This method is actually puts Server's socket into listening mode, it is not blocking func
        # OS knows that only 1 connection is allowed, the rest will be rejected
        self.server_socket.listen(self.MAX_CONNECTIONS)
        print(f"[{self.app}]: Ready and is listening on port 8820...")

        # make server no get stack waiting till client connects but check and keep running and vise versa
        # print(f"[{self.SERVER}]: configured not to stack and wait till the client is connected")
        # self.server_socket.setblocking(False)

        # 6. Server is blocked (stack, pauses, waiting) till first Client (single client) connection. Server will wait forever for the connection
        # first connected client will get the Server from stack, will be returned Client connection details: client_ip, client_socket (only socket actually in use)
        # then server will be stacked waiting for messages from connected client
        print(f"[SERVER]: is paused until client data is arrived")
        self.client_socket, client_address = self.server_socket.accept()
        print(f"[{self.app}]: Connection is established with client ip address: {client_address}, type: {type(self.client_socket)}")

        # 7. create 2 different procs to handle receive and process of the messages from a client
        print(f"[{self.app}]: Creating 2 parallel server activities: receive_client_messages, process_client_messages ...")
        # receiver_proc = multiprocessing.Process(target=self._receive_messages)#, args=(self.client_socket, self.client_messages_queue))
        # processor_proc = multiprocessing.Process(target=self._process_messages)#, args=(self. client_socket, self.client_messages_queue))

        receiver_thread = Thread(target=self._receive_messages)
        processor_thread = Thread(target=self._process_messages)

        # 7. start the activities
        print(f"[{self.app}]: Starting these activities to run")
        receiver_thread.start()
        processor_thread.start()

        receiver_thread.join()
        processor_thread.join()

        # receiver_thread.close()  # no need to close threads (only processes) threads shares memory while processes are not
        # processor_thread.close()
        print(f"[{self.app}]: Server shut down.")

    def _receive_messages(self):
        """
        Looping the server socket, once new message entered, retrieve and handle: insert into internal queue for further respond
        :return: None
        """
        while True:
            print(f"[{self.app}]: process 'receive & store' running ...")
            try:
                # Several scenarios can be here: --------------------------------------------------------------------------------------------------------------------
                # 1: if no incoming message (from a client), server is stack (blocked) and keeps on waiting
                # 2: if incoming message is arrived, the recv() is releases and incoming message can be handled
                # 3: if client closed connection properly (calls close() on its end), the recv() will be released on Server's side
                #    and will return an empty string - Server will get the empty str and will close both (server + client) connection properly
                # 4: if client connection was forcefully disconnected, recv() will return exception that we will catch,
                #    still the Server will close both (server + client) connection properly
                # --------------------------------------------------------------------------------------------------------------------------------------------------
                data = self.client_socket.recv(self.MAX_DATA_SIZE) # its bad idea to do: data = self.client_socket.recv(self.MAX_DATA_SIZE).decode() as a data can be empty
                if not data:
                    print(f"[{self.app}] empty message - is ignored")
                    continue
                    # break # consider here to close the DB

                message_from_client = data.decode('utf-8')
                print(f"[{self.app}]: Received message from a Client: <{message_from_client}>")
                self.client_messages_queue.put(message_from_client)

                if data.decode() == 'q':
                    break
            except ConnectionAbortedError as ee:
                print(f"[{self.app}]: ### Receive error: Client connection forcefully terminated, error:\n {ee} ###")
                break # consider here to close the DB

        # # 7. Server closes the connection - in any way either if client disconnected properly or if client's connection forcefully closed
        # # If the server doesn’t call close(), the socket could remain in a "half-closed" state
        # # where resources are still being held open even though the client is no longer connected.
        # # Server MUST close Clients connection and his own Server connection according to the protocol
        # print(f"[{self.SERVER}]: Closing Client socket (connection) ")
        # self.client_socket.close()
        # print(f"[{self.SERVER}]: Closing Server socket (connection) ")
        # self.server_socket.close()
        # print(f"[{self.SERVER}]: processes finished !!!")

    def _process_messages(self) -> None:
        """
        Looping the server queue, once new message entered, retrieve and respond
        :return:
        """
        index = 0

        while True:
            print(f"[{self.app}]: process 'retrieve & respond' running ...")
            try:
                # .get() is for retrieve message from queue
                # default it is blocking function but we can set a time parameter to limit the blocking time to 1 sec
                # If no message arrives within 1 second, it raises queue.Empty, which we're catching to simply continue the loop

                message = self.client_messages_queue.get(timeout=8)
                self.connection_store.setdefault(index, []).append(message)

                # check message, if empty then finish
                if message == 'q':
                    print(f"[{self.app}]: extracted message = {message}, finish polling the queue")
                    break  # consider here to close the DB

                # respond to a client
                resp_message = "Hello, client! I received your message."
                print(f"[{self.app}]: Sending response message back to client: {index}.{resp_message}")
                self.client_socket.sendall(resp_message.encode())
                self.connection_store.setdefault(index, []).append(resp_message)
                index += 1
                print(f"[{self.app}]: Message sent !")

            except queue.Empty:
                print(f"[{self.app}]: yet found any message in queue, keep polling the queue ...")
                continue
            except Exception as e:
                print(f"[{self.app}]: Queue processing error: {e} ###")
                break
        print(f"[{self.app}]: processes finished !!!")

    def disconnect(self):
        # 7. Server closes the connection - in any way either if client disconnected properly or if client's connection forcefully closed
        # If the server doesn’t call close(), the socket could remain in a "half-closed" state
        # where resources are still being held open even though the client is no longer connected.
        # Server MUST close Clients connection and his own Server connection according to the protocol
        print(f"[{self.app}]: Closing Client socket (connection) ")
        self.client_socket.close()
        print(f"[{self.app}]: Closing Server socket (connection) ")
        self.server_socket.close()
        print(f"[{self.app}]: processes finished !!!")

    def print_received_messages(self):
        print(f"\n[{self.app}]: All the messages that were sent: Client -> Server\n"
              f"--------------------------------------------------------------------")
        print(f"the len of the store is: {len(self.connection_store)}")
        for index, messages_list in self.connection_store.items():
            print(f"[{self.app}]: [{index}]: {messages_list}")

# I added here a main just in case I wish to run the server directly and not from simpl_client_server_app.py
if __name__ == '__main__':
    server = Server()
    server.start()

    print(f"Server shutting down ")
    server.disconnect()

    server.print_received_messages()