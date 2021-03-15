#!/usr/bin/env python3

########################################################################
#
# GET File Transfer
#
# When the client connects to the server, it immediately sends a
# 1-byte GET command followed by the requested filename. The server
# checks for the GET and then transmits the file. The file transfer
# from the server is prepended by an 8 byte file size field. These
# formats are shown below.
#
# The server needs to have REMOTE_FILE_NAME defined as a text file
# that the client can request. The client will store the downloaded
# file using the filename LOCAL_FILE_NAME. This is so that you can run
# a server and client from the same directory without overwriting
# files.
#
########################################################################

import socket
import argparse
import os
import threading

########################################################################

# Define all of the packet protocol field lengths. See the
# corresponding packet formats below.
CMD_FIELD_LEN = 1 # 1 byte commands sent from the client.
FILE_SIZE_FIELD_LEN  = 8 # 8 byte file size field.
RESONSE_LEN = 1

# Packet format when a GET command is sent from a client, asking for a
# file download:

# -------------------------------------------
# | 1 byte GET command  | ... file name ... |
# -------------------------------------------

# When a GET command is received by the server, it reads the file name
# then replies with the following response:

# -----------------------------------
# | 8 byte file size | ... file ... |
# -----------------------------------

# Define a dictionary of commands. The actual command field value must
# be a 1-byte integer. For now, we only define the "GET" command,
# which tells the server to send a file.

CMD = { "GET" : 1 , "PUT" : 2, "LIST" : 3}

MSG_ENCODING = "utf-8"
    
########################################################################
# SERVER
########################################################################

class Server:

    HOSTNAME = "127.0.0.1"

    PORT = 30001
    SERVICE_SCAN_PORT = 30000
    SDP_MSG = "Aayush, Eric, William, and Adam's Sharing Service"
    SERVICE_DISCOVER_COMMAND = "SERVICE DISCOVERY"
    SDP_MSG_ENCODED = SDP_MSG.encode(MSG_ENCODING)
    
    RECV_SIZE = 1024
    BACKLOG = 5

    FILE_NOT_FOUND_MSG = "Error: Requested file is not available!"
    MSG_ENCODING = "utf-8"

    # This is the directory that the server will use.
    REMOTE_DIRECTORY = "./server/"

    def __init__(self):
        self.print_files()
        self.create_udp_socket()
        self.create_listen_socket()
        self.process_connections_forever()

    def create_udp_socket(self):            
        # Create an IPv4 UDP socket.
        self.service_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Get socket layer socket options.
        self.service_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Bind socket to socket address, i.e., IP address and port.
        self.service_socket.bind( (Server.HOSTNAME, Server.SERVICE_SCAN_PORT) )
        
        thread_udp = threading.Thread(target = self.process_udp_connections_forever,args = [])
        thread_udp.start()
        print("UDP: Listening for service discovery messages on SDP port {} ...".format(Server.SERVICE_SCAN_PORT))
        
    def create_listen_socket(self):
        try:
            # Create the TCP server listen socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((Server.HOSTNAME, Server.PORT))
            self.socket.listen(Server.BACKLOG)
            print("TCP: Listening for file sharing connections on port {} ...".format(Server.PORT))
        except Exception as msg:
            print(msg)
            exit()
            
    def process_udp_connections_forever(self):
       while True:
            try:
                recvd_bytes, address = self.service_socket.recvfrom(Server.RECV_SIZE)

                print("Received: ", recvd_bytes.decode('utf-8'), " Address:", address)
            
                # Decode the received bytes back into strings.
                recvd_str = recvd_bytes.decode(Server.MSG_ENCODING)

                # Check if the received packet contains a service scan
                # command.
                if Server.SERVICE_DISCOVER_COMMAND in recvd_str:
                    # Send the service advertisement message back to
                    # the client.
                    self.service_socket.sendto(Server.SDP_MSG_ENCODED, address)
            except KeyboardInterrupt:
                print()
                exit(1)
                
    def process_connections_forever(self):
        try:
            while True:
                thread_tcp = threading.Thread(target = self.connection_handler, args = (self.socket.accept(),))
                thread_tcp.start()
        except KeyboardInterrupt:
            print()
        finally:
            self.socket.close()

    def connection_handler(self, client):
        connection, address = client
        print("-" * 72)
        print("Connection received from {}.".format(address))

        # Read the command and see if it is a GET.
        while(True):
            bytes = connection.recv(CMD_FIELD_LEN)
            if len(bytes) < CMD_FIELD_LEN:
                print("Client {} connection terminated.".format(address))
                connection.close()
                return
                
            cmd = int.from_bytes((bytes), byteorder='big')
            if cmd == CMD["GET"]:
                self.cmd_get_handler(client)
            elif cmd == CMD["PUT"]:
                self.cmd_put_handler(client)
            elif cmd == CMD["LIST"]:
                self.cmd_list_handler(client)
            else:
                print("Invalid command received!")
        
    def cmd_get_handler(self, client):
        connection, address = client
    
        # Now read and decode the requested filename.
        filename_bytes = connection.recv(Server.RECV_SIZE)
        filename = filename_bytes.decode(MSG_ENCODING)

        # Open the requested file and get set to send it to the
        # client.
        
        try:
            file = open(Server.REMOTE_DIRECTORY+filename, 'r').read()
        except FileNotFoundError:
            print(Server.FILE_NOT_FOUND_MSG)
            file_size_bytes = 0
            pkt = file_size_bytes.to_bytes(FILE_SIZE_FIELD_LEN, byteorder='big')
            connection.sendall(pkt)
            return

        # Encode the file contents into bytes, record its size and
        # generate the file size field used for transmission.
        file_bytes = file.encode(MSG_ENCODING)
        file_size_bytes = len(file_bytes)
        file_size_field = file_size_bytes.to_bytes(FILE_SIZE_FIELD_LEN, byteorder='big')

        # Create the packet to be sent with the header field.
        pkt = file_size_field + file_bytes
        
        try:
            # Send the packet to the connected client.
            connection.sendall(pkt)
            print("Sending file: ", filename)
        except socket.error:
            # If the client has closed the connection, close the
            # socket on this end.
            print("Closing client connection ...")
            connection.close()
            return
        
    def cmd_put_handler(self, client):
        connection, address = client
    
        # Now read and decode the requested filename.
        filename_bytes = connection.recv(Server.RECV_SIZE)
        filename = filename_bytes.decode(MSG_ENCODING)

        try:
            open(Server.REMOTE_DIRECTORY+filename, 'r')
            print("File already exists locally.")
            response = 0
        except:
            response = 1
            
        try:
            pkt = response.to_bytes(RESONSE_LEN, byteorder='big')
            connection.sendall(pkt)
        except socket.error:
            # If the client has closed the connection, close the
            # socket on this end.
            print("Closing client connection ...")
            connection.close()
            return
        
        # Exiting without waiting for data
        if not response:
            return
        
        # Encode the file contents into bytes, record its size and
        # generate the file size field used for transmission.
        file_size_bytes = connection.recv(FILE_SIZE_FIELD_LEN)
        file_size = int.from_bytes(file_size_bytes, byteorder='big')

        # Receive the file itself.
        recvd_bytes_total = bytearray()
        try:
            # Keep doing recv until the entire file is uploaded. 
            while len(recvd_bytes_total) < file_size:
                recvd_bytes_total += connection.recv(Server.RECV_SIZE)

            # Create a file using the received filename and store the data.
            print("Received {} bytes. Creating file: {}" \
                  .format(len(recvd_bytes_total), Server.REMOTE_DIRECTORY+filename))

            with open(Server.REMOTE_DIRECTORY+filename, 'w') as f:
                f.write(recvd_bytes_total.decode(MSG_ENCODING))
        except socket.error:
            # If the client has closed the connection, close the
            # socket on this end.
            connection.close()
    
    
    def cmd_list_handler(self, client):
        connection, address = client
    
        files = []
        for (dirpath, dirnames, filenames) in os.walk(Server.REMOTE_DIRECTORY):
            files.extend(filenames)
            break
        
        file_listing = ""
        for f in files:
            file_listing += "- "+f+"\n"
        
        # Now read and decode the requested filename.
        file_bytes = file_listing.encode(MSG_ENCODING)
        file_size_bytes = len(file_bytes)
        file_size_field = file_size_bytes.to_bytes(FILE_SIZE_FIELD_LEN, byteorder='big')

        # Create the packet to be sent with the header field.
        pkt = file_size_field + file_bytes
        
        try:
            # Send the packet to the connected client.
            connection.sendall(pkt)
            print("Sending file listing:")
            print(file_listing)
        except socket.error:
            # If the client has closed the connection, close the
            # socket on this end.
            print("Closing client connection ...")
            connection.close()
            return
    def print_files(self):
        files = []
        for (dirpath, dirnames, filenames) in os.walk(Server.REMOTE_DIRECTORY):
            files.extend(filenames)
            break

        for f in files:
            print("- "+f)
        print()

########################################################################
# CLIENT
########################################################################

class Client:

    RECV_SIZE = 1024
    
    # Define the local file name where the downloaded file will be
    # saved.
    # This is the directory that the client will use.
    LOCAL_DIRECTORY = "./client/"

    def __init__(self):
        self.client_CMD = { "SCAN" : 0, "GET" : 1 , "PUT" : 2, "RLIST" : 3, "LLIST" : 4, "CONNECT" : 5, "BYE" : 6}
        self.create_udp_socket()
        self.command_handle()

    def create_udp_socket(self):
        try: 
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        except Exception as msg:
            print(msg)
            exit()
    
    def discover_service(self):
        print("Attempting to Discover Service")
        try:
            self.udp_socket.sendto(b"SERVICE DISCOVERY", (Server.HOSTNAME, Server.SERVICE_SCAN_PORT))
            msg_bytes, address_port = self.udp_socket.recvfrom(Client.RECV_SIZE)
            print("Received: ", msg_bytes.decode('utf-8'), " IP/Port:", address_port)
        except:
            print("No service found.")
    
    def get_socket(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        except Exception as msg:
            print(msg)
            exit()

    def socket_recv_size(self, length):
        bytes = self.socket.recv(length)
        if len(bytes) < length:
            self.socket.close()
            exit()
        return(bytes)

    def split_up_string(self, x):
        hold = []
        hold_string = ""
        flag = 0
        for i in range(0,len(x)):
            
            if(flag == 1 or i == len(x)-1):
                if(x[i] != " " and i == len(x)-1):
                    hold_string += x[i]
                hold.append(hold_string)
                hold_string = ""
                flag = 0
                
            if(flag == 0):
                if(x[i] != " "):
                    hold_string += x[i]
                else:
                    flag = 1
        return hold

    def command_handle(self):
        # This will be an infinite loop that will handle initialization to 
        # connection etc
        connected = False
        while(True):
            command = input("Command:")
            command_words = self.split_up_string(command)
            try:
                x = self.client_CMD[command_words[0].upper()]
            except:
                x = -1 #arbitrary number not on the commands list

            if(x == 0):
                    self.discover_service()
            if(x == 1):
                if connected:
                    self.get_file(command_words[1])
                else:
                    print("Client not connected")
            if(x == 2):
                if connected:
                    self.put_file(command_words[1])
                else:
                    print("Client not connected")
            if(x == 3):
                if connected:
                    self.get_fileList()
                else:
                    print("Client not connected")
            if(x == 4):
                self.local_list()
            if(x == 5):
                self.connect_to_server(command_words[1], command_words[2])
                connected = True
            if(x == 6):
                self.bye_to_server()
                connected = False

    def get_file(self, filename):
        # Create the packet GET field.
        get_field = self.client_CMD["GET"].to_bytes(CMD_FIELD_LEN, byteorder='big')

        # Create the packet filename field.
        filename_field = filename.encode(MSG_ENCODING)

        # Create the packet.
        pkt = get_field + filename_field

        # Send the request packet to the server.
        self.socket.sendall(pkt)

        # Read the file size field.
        file_size_bytes = self.socket_recv_size(FILE_SIZE_FIELD_LEN)
        if len(file_size_bytes) == 0:
            print("File not found")
            return

        # Make sure that you interpret it in host byte order.
        file_size = int.from_bytes(file_size_bytes, byteorder='big')

        # Receive the file itself.
        recvd_bytes_total = bytearray()
        try:
            # Keep doing recv until the entire file is downloaded. 
            while len(recvd_bytes_total) < file_size:
                recvd_bytes_total += self.socket.recv(Client.RECV_SIZE)

            # Create a file using the received filename and store the
            # data.
            print("Received {} bytes. Creating file: {}" \
                  .format(len(recvd_bytes_total), Client.LOCAL_DIRECTORY+filename))

            with open(Client.LOCAL_DIRECTORY+filename, 'w') as f:
                f.write(recvd_bytes_total.decode(MSG_ENCODING))
        except KeyboardInterrupt:
            print()
            exit(1)
        # If the socket has been closed by the server, break out
        # and close it on this end.
        except socket.error:
            self.socket.close()
    
    def put_file(self, filename):
        try:
            file = open(Client.LOCAL_DIRECTORY+filename, 'r').read()
        except FileNotFoundError:
            print("File not found.")
            return

        # Create the packet PUT field.
        put_field = self.client_CMD["PUT"].to_bytes(CMD_FIELD_LEN, byteorder='big')
        
        # Create the packet filename field.
        filename_field = filename.encode(MSG_ENCODING)

        # Create the packet
        pkt = put_field + filename_field
        # Send the request packet to the server
        self.socket.sendall(pkt)

        response_bytes = self.socket_recv_size(RESONSE_LEN)
        response = int.from_bytes(response_bytes, byteorder='big')
        if not response:
            print("File already exists on server.")
            return

        # Encode the file contents into bytes, record its size and
        # generate the file size field used for transmission.
        file_bytes = file.encode(MSG_ENCODING)
        file_size_bytes = len(file_bytes)
        file_size_field = file_size_bytes.to_bytes(FILE_SIZE_FIELD_LEN, byteorder='big')

        # Create the packet to be sent with the header field.
        pkt = file_size_field + file_bytes
        
        try:
            # Send the packet to the connected client.
            self.socket.sendall(pkt)
            print("Sending file: ", filename)
        except socket.error:
            # If the client has closed the connection, close the
            # socket on this end.
            print("Closing server connection ...")
            self.socket.close()
            return
        
    def get_fileList(self):
        # Create the packet GET field.
        get_field = self.client_CMD["RLIST"].to_bytes(CMD_FIELD_LEN, byteorder='big')
        pkt = get_field

        # Send the request packet to the server
        self.socket.sendall(pkt)
        
        # Read the list size field.
        list_size_bytes = self.socket_recv_size(FILE_SIZE_FIELD_LEN)
        if len(list_size_bytes) == 0:
            print("No files found")
            return

        # Make sure that you interpret it in host byte order.
        list_size = int.from_bytes(list_size_bytes, byteorder='big')

        # Receive the file itself.
        recvd_bytes_total = bytearray()
        try:
            # Keep doing recv until the entire file is downloaded. 
            while len(recvd_bytes_total) < list_size:
                recvd_bytes_total += self.socket.recv(Client.RECV_SIZE)

            # Output the recieved list
            print("Remote Directory:")
            print(recvd_bytes_total.decode(MSG_ENCODING))
        except KeyboardInterrupt:
            print()
            exit(1)
        # If the socket has been closed by the server, break out
        # and close it on this end.
        except socket.error:
            self.socket.close()
    
    def local_list(self):
        # Reading the files in the local directory
        files = []
        for (dirpath, dirnames, filenames) in os.walk(Client.LOCAL_DIRECTORY):
            files.extend(filenames)
            break
        
        # Outputting the filenames
        print("Local Directory:")
        for f in files:
            print("- "+f)
        print()
        
    def connect_to_server(self, server_IP, server_port):
        #print(server_IP)
        #print(server_port)
        try:
            self.get_socket()
            self.socket.connect((str(server_IP), int(server_port)))#((Server.HOSTNAME, Server.PORT))
        except Exception as msg:
            print(msg)
            exit()
    
    def bye_to_server(self):
        try:
            self.socket.close()
        except:
            print("Socket doesn't exist")
            
########################################################################

if __name__ == '__main__':
    roles = {'client': Client,'server': Server}
    parser = argparse.ArgumentParser()

    parser.add_argument('-r', '--role',
                        choices=roles, 
                        help='server or client role',
                        required=True, type=str)

    args = parser.parse_args()
    roles[args.role]()

########################################################################






