import os
import threading
from threading import Thread
import queue
import socket
import yaml
from typing import Final # makes my types be final without ability to change their type
import ssl
from colorama import Fore, Style, init # for printing in colors

# required for multi client
import select

colors_dict = {0: Fore.YELLOW,
               1: Fore.CYAN,
               2: Fore.RED,
               3: Fore.BLUE,
               4: Fore.GREEN,
               5: Fore.MAGENTA,
               6: Fore.LIGHTRED_EX,
               7: Fore.LIGHTBLUE_EX,
               8: Fore.LIGHTCYAN_EX,
               9: Fore.LIGHTGREEN_EX}

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
        self.IP: str = None
        self.PORT: str= None
        self.MAX_CONNECTIONS: int = 1
        self.NUMBER_WORKING_THREADS = 0
        self.server_socket = None
        self.all_clients_messages_queue = queue.Queue() # this Q was created in context of the Server obj, therefore will leave also after thread will finish
        self.monitored_client_sockets_list = []
        self.monitored_bad_client_sockets_list = []
        self.all_clients = {}
        self.received_messages_store = {}

    def _init_colors(self):
        init() # Initialize colorama (needed for Windows)

    def _find_full_file_path(self, filename):
        for dirpath, _, filenames in os.walk(os.getcwd()):
            if filename in filenames:
                full_file_path = os.path.join(dirpath, filename)  # Return full path if found
                return full_file_path
        return None  # Return None if not found

    def _init(self):
        self._init_colors()
        print(f"[{self.app}]: app is executed with the next parameters: ")

        full_path_to_file = self._find_full_file_path("server_config.yaml")
        print(f"[{self.app}]: Loading configuration for the server from: {full_path_to_file}")
        if not full_path_to_file:
            raise FileExistsError


        with open(full_path_to_file, "r") as yaml_file:
            config = yaml.safe_load(yaml_file)

            self.IP = config["server"]["ip_address"]  # also possible to do: socket.gethostbyname(socket.gethostname()) if not ip else ip  # <---- this way we determine the local host address, this way -> we set it hard codded: "127.0.0.1" if not ip else ip
            print(f"[{self.app}]: IP: {self.IP}")

            self.PORT = config["server"]["port"]  # also possible to do: 8820 if not port else port
            print(f"[{self.app}]: PORT: {self.PORT}")

            self.MAX_DATA_SIZE = config["server"]["max_data_size"]
            print(f"[{self.app}]: Max data size: {self.MAX_DATA_SIZE}")

            self.NUMBER_WORKING_THREADS = config["server"]["number_working_threads"]
            print(f"[{self.app}]: Number working threads: {self.NUMBER_WORKING_THREADS}")

    def _create_server_socket(self):
        # 1. Create a socket object
        print(f"\n\n[{self.app}]: Creating the 'regular' TCP/IP socket ...")
        self.server_socket = socket.socket(socket.AF_INET,
                                           socket.SOCK_STREAM)  # use protocol: TCP

        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

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
        print(f"[{self.app}]: Wrapping the 'regular' TCP/IP socket to be SSL 'secured' socket ...")
        self.server_socket = context.wrap_socket(self.server_socket,
                                                 server_side=True)  # <--- this line tells python that this is a Server and not a Client

        # 4. Bind the socket (secured socket) to an address and port
        self.server_socket.bind((self.IP, self.PORT))

        # 5. This method is actually puts Server's socket into listening mode, it is not blocking func
        # OS knows that only 1 connection is allowed, the rest will be rejected
        self.server_socket.listen()
        print(f"[{self.app}]: Ready and is listening on port 8820...")

    def _create_working_threads(self, NUM_WORKERS):
        """
        :param NUM_WORKERS: amount of working threads
        flag daemon means:
            daemon = False means: The main program will wait for the thread to finish before main program exits <- this is what we need
            daemon = True means: when main program finishes, all threads will finish automatically
        :return:
        """
        print(f"[{self.app}]: this machine has: {os.cpu_count()} cores, but will be used {NUM_WORKERS} processing threads")
        # This line starts n worker threads that will all run (execute) the 'same' worker() function at the same time — in parallel.
        # all n threads will 'sit' on the Q waiting for new task (new message) task (= message from Client).
        # when new message appears in queue, any free thread can pick up the message and handle it.
        # if will be more than 1 free thread the OS will decide who will handle new message
        print(f"[{self.app}]: creating {NUM_WORKERS} working threads to process incoming messages from clients ...")
        for cnt in range(NUM_WORKERS):
            threading.Thread(target=self._working_thread,
                             name=f"working_thread_{cnt}",
                             daemon=True).start() # see comment about this flag !!

    def _accept_new_socket(self):
        # this case will run when the server receives a new incoming client connection.
        # server socket is notified (triggered) only when new client socket tries to connect it from the Client side
        print(Fore.LIGHTGREEN_EX + f"{[self.app]}: new client connection arrived, will be accepted")
        client_socket, client_address = self.server_socket.accept()
        # adding new client socket to the list, next time this client will send messages -> server will know it
        # without adding to the list, server will not notice messages from this connection
        self.monitored_client_sockets_list.append(client_socket)
        print(Fore.LIGHTGREEN_EX + f"{[self.app]}: new Client connection: IP: {client_address}, was added to the list of monitored sockets")
        # we also store client sockets for loging, debug, ...
        self.all_clients[client_socket] = client_address

    def _receive_new_message(self, notified_socket) -> bool:
        """
        extract data (message) from socket and put in queue, if received data is 'q'
        :param notified_socket:
        :return:
        """
        # extract from socket
        client_address = self.all_clients[notified_socket]
        print(Fore.LIGHTGREEN_EX + f"{[self.app]}: extracting data that arrived on existing client socket address {client_address}, will be received")
        try:
            # get new data from socket
            message = notified_socket.recv(self.MAX_DATA_SIZE)
            print(Fore.LIGHTGREEN_EX + f"[{self.app}]: received data: {message} from client: {client_address}")

            # check if data isnt empty or isnt 'q' - if data ok, put in the Q
            if message and message.decode() != 'q':
                # method .put() is already thread safe so no need locks / mutexes
                self.all_clients_messages_queue.put((notified_socket,
                                                     client_address,
                                                     message.decode('utf-8')))
            else: # empty data (client disconnected forcibly) or message = 'q' (client sent disconnection message)
                print(Fore.LIGHTGREEN_EX + f"[{self.app}]: client: {client_address} - disconnected")
                # deleting client socket from list
                self.monitored_client_sockets_list.remove(notified_socket)
                # closing this client socket
                notified_socket.close()
                # deleting the client socket from dict (key is socket obj, value client address)
                self.all_clients.pop(notified_socket)

                # check if server can finish
                if not self.monitored_client_sockets_list and not self.all_clients:
                    print(Fore.LIGHTGREEN_EX + f"[{self.app}]: main process is finished")
                    return False
                print(Fore.LIGHTGREEN_EX + f"[{self.app}]: main process keep on running because more client/s are still running")

        except ConnectionAbortedError as ee:
            print(Fore.LIGHTGREEN_EX + f"[{self.app}]: ### Receive error: Client connection forcefully terminated, error:\n {ee} ###")
            # deleting client socket from list
            self.monitored_client_sockets_list.remove(notified_socket)
            # closing this client socket
            notified_socket.close()
            # deleting the client socket from dict (key is socket obj, value client address)
            if notified_socket in self.all_clients:
                del self.all_clients[notified_socket]
            return False # finish
        return True # keep monitoring

    def _scan_sockets(self):
        """
        monitoring loop, using select method that scans 3 type of lists:
        list of sockets from which we wish to read in case will be new message there
        2. list of sockets to which we wish to write  <-- this one we can ignore
        3. list of special sockets                    <-- this one we can ignore

        by using method Select - I actually ask this:
        Tell me:
        Which sockets are ready to be read (new connection = new socket connected | new data arrived on existing socket),
        and which sockets have errors,  from my list of tracked sockets.”

        method 'select' get 3 lists to monitor but even if at the beginning the list is empty, over time it can be filled with sockets so it is breathing lists

        why we ask to monitor bad sockets?
        socket can be broken even if we dont send/receive on it - simple reason -> Client closed it, or timeout or internal error or ....
        Server must know if Client was broken and will read from dead socked - to avoid it simply check the sock and if socket in the bad list - remove the bad socket from monitoring list and never use it again
        select is blocking method until at least 1 socket is ready for reading or has an exception, if it is a client socket - then go receive its data.

        !! correct manner:
        we see here that accepting new connections is done in main process of the server while the listening on the queue is done in separate working threads !!
        """

        # decide upon how many working threads you will have:
        # usually it depends on how many cores you PC has
        self._create_working_threads(self.NUMBER_WORKING_THREADS)

        # start scanning sockets
        while True:
            print(Fore.LIGHTGREEN_EX + f"{[self.app]}: main process is scanning the sockets ...")
            readable_sockets_list, _, bad_sockets_list = select.select([self.server_socket] + self.monitored_client_sockets_list,# read list - this is a list of all sockets we monitor (=all client sockets but also a server_socket)
                                                                  [],  # write list
                                                                       self.monitored_bad_client_sockets_list,# list of broken sockets - we are going to collect such sockets so we supply a list that at the beginning is empty but if will be broken socket it will be placed in this list and monitored
                                                                5)  # <--- this timeout says that select will not be blocking func, after timeout we will go and check if were new messages / new client has connected
            # we are here because were some change in the monitored sockets:
            # change can be on the server socket - new client connection arrived
            # or
            # new message arrived at one of the existing client connections
            # lets find out
            for notified_socket in readable_sockets_list:
                if notified_socket is self.server_socket:
                    self._accept_new_socket()
                else:
                    if not self._receive_new_message(notified_socket):
                        return

            for notified_socket in bad_sockets_list:
                self.monitored_client_sockets_list.remove(notified_socket)
                if notified_socket in self.all_clients:
                    del self.all_clients[notified_socket]
                notified_socket.close()

    # this is a worker thread func
    def _working_thread(self) -> None:
        """
        This is a method that each working thread will run.
        Each working thread will extract from Q only valid messages
        Each working thread is looping the server queue, once new message entered, the OS decides which on of the processes is free to retrieve the message and to process it
        :return:
        """
        index = 0
        col = int(threading.current_thread().name.split('_')[2])
        print(colors_dict[col] + f"[{self.app}]: process: {threading.current_thread().name} started running ...")

        while True:
            try:
                # .get() is for retrieve message from queue. We retrieve what we put (if we put tuples we should get tuples)
                # default it is blocking function but we can set a time parameter to limit the blocking time to 1 sec
                # If no message arrives within 1 second, it raises queue.Empty, which we're catching to simply continue the loop
                print(colors_dict[col] + f"[{self.app}]: process: {threading.current_thread().name} tries to get a message from a queue ...")
                client_socket_obj, client_address, message = self.all_clients_messages_queue.get(timeout=8) # method .get() is already thread safe so no need locks / mutexes

                # respond to a client
                resp_message = f"Hello, client! I received your message: {message}."
                print(colors_dict[col] + f"[{self.app}]: Sending response message back to client: {client_socket_obj}, [{index}]:{resp_message}")
                try:
                    client_socket_obj.sendall(resp_message.encode())
                except Exception as ee:
                    print(colors_dict[col] + f"[{self.app}]: failed sending response to client: {client_socket_obj}, error: {ee}")
                else:
                    print(colors_dict[col] + f"[{self.app}]: message sent !")
                    # storing all
                    print(colors_dict[col] + f"[{self.app}]: storing message in internal data base ...")
                    self.received_messages_store.setdefault(client_address, []).append((index, message, resp_message))
                    index += 1
                finally:
                    self.all_clients_messages_queue.task_done()
            except queue.Empty:
                print(colors_dict[col] + f"[{self.app}]: keep polling the queue ...")
                continue
            except Exception as e:
                print(colors_dict[col] + f"[{self.app}]: failed processing message from a queue: {e} ###")
                return
        print(colors_dict[col] + f"[{self.app}]: process: {threading.current_thread().name} - finished")

    def disconnect(self):
        """
        Server closes both server socket and clients sockets
        :return:
        """
        print(Fore.LIGHTGREEN_EX + f"[{self.app}]: Closing Server socket (connection) ")
        self.server_socket.close()
        print(Fore.LIGHTGREEN_EX + f"[{self.app}]: Server socket is closed + all client sockets are close, app is finished !!!")

    def print_received_messages(self):
        print(Fore.LIGHTGREEN_EX + f"\n[{self.app}]: All the messages that were sent: Client -> Server\n")

        #print(f"the len of the store is: {len(self.received_messages_store)}")
        for client_address, all_client_messages_list in self.received_messages_store.items():
            print(Fore.LIGHTGREEN_EX + f"\n\n[{self.app}]: Client: [{client_address}], messages are: ")
            for message in all_client_messages_list:
                print(Fore.LIGHTGREEN_EX + f"[{self.app}]: {message}")

    def start(self):
        self._init()
        self._create_server_socket()
        self._scan_sockets()


# I added here a main just in case I wish to run the server directly and not from simpl_client_server_app.py
if __name__ == '__main__':
    server = Server()
    server.start()
    server.disconnect()
    server.print_received_messages()