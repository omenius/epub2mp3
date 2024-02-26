from sys import argv, stdin

if len(argv) > 1:
    text = argv[1]
elif not stdin.isatty():
    text = stdin.read()
else:
    exit()

import socket

# Set the path for the Unix socket
socket_path = '/tmp/say_socket'

# Create the Unix socket client
client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

# Connect to the server
try:
    conn = client.connect(socket_path)
except FileNotFoundError:
    print('Server is offline')
    exit()

# Send a message to the server
client.send(text.encode())

# Close the connection
client.close()

