from simple_client_server.client_tcp import Client
from simple_client_server.server_tcp import Server


from typing import Final # makes my types be final without ability to change their type

if __name__ == '__main__':
    ip: Final[str] = "127.0.0.1"
    port: Final[int] = 8820

    server = Server(ip, port)
    server.start_server()
    # client started waiting till client connect it

    client = Client(ip, port)
    while True:
        message = input("Enter message (empty message to exit):").rstrip()
        if not message:
            print(f"User did not enter message, Client will disconnect ")
            break
        print(f"Message to send to server: {message}")
    client.disconnect_client()