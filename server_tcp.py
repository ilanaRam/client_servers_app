import socket
from typing import Final # makes my types be final without ability to change their type


class Server:
    ############################################################################################
    # Server SOCKET:
    # create socket (of the type: ip socket, using TCP protocol)
    # bind (to its ip and port)
    # listen (put server socket into listen state)
    # accept (blocking wait for Client connection)
    # recv (blocking wait for Client data) -> return answer
    ############################################################################################

    def __init__(self, ip, port):
        self.ip: Final[str] = "127.0.0.1" if not ip else ip
        self.port: Final[int] = 8820 if not port else port

        self.MAX_CONNECTIONS: Final[int] = 1
        self.MAX_DATA_SIZE: Final[int] = 1024 # 1KB
        self.SERVER: Final[str] = "SERVER"
        self.client_socket = None
        self.server_socket = None

    def start_server(self):
        # 1. Create a socket object
        print(f"[{self.SERVER}]: Creating the socket ...")
        self.server_socket = socket.socket(socket.AF_INET,
                                           socket.SOCK_STREAM) # Protocol: TCP
        #self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # 2. Bind the socket to an address and port
        print(f"[{self.SERVER}]: Connecting the socket to ip: {self.ip}, port: {self.port} ...")
        self.server_socket.bind((self.ip, self.port))

        # 3. This method is actually puts Server's socket into listening mode, it is not blocking func
        # OS knows that only 1 connection is allowed, the rest will be rejected
        self.server_socket.listen(self.MAX_CONNECTIONS)
        print(f"[{self.SERVER}]: Ready and is listening on port 8820...")

        # make server no get stack waiting till client connects but check and keep running and vise versa
        # print(f"[{self.SERVER}]: configured not to stack and wait till the client is connected")
        # self.server_socket.setblocking(False)

        # 4. Server is blocked (stack, pauses, waiting) till first Client (single client) will connect. Server will wait forever for the connection
        # first connected client will get the Server from stack, will be returned Client connection details: client_ip, client_socket (only socket actually in use)
        # then server will be stacked waiting for data
        print(f"[SERVER]: is paused until client data is arrived")
        self.client_socket, client_address = self.server_socket.accept()
        print(f"[{self.SERVER}]: Connection is established with client ip address: {client_address}, type: {type(self.client_socket)}")

        # 5. Server will be stacked waiting to extract data fromm the client socket, till the data is received the server is stacked
        while True:
            try:
                print(f"[{self.SERVER}]: Try to receive a data from a client ...")
                # --------------------------------------------------------------------------------------------------------------------------------------------------
                # option_1: if no data, server is waiting, it is blocked
                # option_2: if data arrived recv() is releases and data is handled
                # option_3: if client closed connection properly (calls close() on its end) the recv() will return empty string that is why I check for empty string
                # option_4: if client connection was forcefully disconnected, recv() will return exception tha twe will catch
                # --------------------------------------------------------------------------------------------------------------------------------------------------
                data = self.client_socket.recv(self.MAX_DATA_SIZE).decode()
                print(f"[{self.SERVER}]: Received data from Client: <{data}>, lets check the content ...")

                if not data:
                    print(f"[{self.SERVER}]: CHECK: Received empty Data from client - means Client closed correctly its connection")
                    break
                else:
                    # 6. Send a response back to the client
                    resp_message = "Hello, client! I received your message."
                    print(f"[{self.SERVER}]: Sends back this answer to client: {resp_message}")
                    self.client_socket.send(resp_message.encode())
                    print(f"[{self.SERVER}]: Message sent ..")

            except ConnectionAbortedError as ee:
                print(f"[{self.SERVER}]: ### Client connection forcefully terminated, error:\n {ee} ###")
                break

        # 7. Server closes the connection - in any way either if client disconnected properly or if client's connection forcefully closed
        # If the server doesn’t call close(), the socket could remain in a "half-closed" state
        # where resources are still being held open even though the client is no longer connected.
        # Server MUST close Clients connection and his own Server connection according to the protocol
        print(f"[{self.SERVER}]: Closing Client socket (connection) ")
        self.client_socket.close()

        print(f"[{self.SERVER}]: Closing Server socket (connection) ")
        self.server_socket.close()

# I added here a main just in case I wish to run the server directly and not from simpl_client_server_app.py
if __name__ == '__main__':
    ip: Final[str] = "127.0.0.1"
    port: Final[int] = 8820

    server = Server(ip, port).start_server()

    # server started waiting till client connects it