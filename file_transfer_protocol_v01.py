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
########################################################################

# Define all of the packet protocol field lengths. See the
# corresponding packet formats below.
CMD_FIELD_LEN = 1 # 1 byte commands sent from the client.
FILE_SIZE_FIELD_LEN  = 8 # 8 byte file size field.

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
    SDP_MSG_ENCODED = SDP_MSG.encode(MSG_ENCODING)
    RECV_SIZE = 1024
    BACKLOG = 5

    FILE_NOT_FOUND_MSG = "Error: Requested file is not available!"

    # This is the file that the client will request using a GET.
    REMOTE_FILE_NAME = "remotefile.txt"
    # REMOTE_FILE_NAME = "bee.jpg"

    def __init__(self):
        self.create_listen_socket()
        self.process_connections_forever()

    def create_listen_socket(self):
        try:
            # Create the TCP server listen socket in the usual way.
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((Server.HOSTNAME, Server.PORT))
            self.socket.listen(Server.BACKLOG)
            print("Listening on port {} ...".format(Server.PORT))
        except Exception as msg:
            print(msg)
            exit()

    def process_connections_forever(self):
        try:
            while True:
                self.connection_handler(self.socket.accept())
        except KeyboardInterrupt:
            print()
        finally:
            self.socket.close()

    def connection_handler(self, client):
        connection, address = client
        print("-" * 72)
        print("Connection received from {}.".format(address))

        # Read the command and see if it is a GET.
        cmd = int.from_bytes(connection.recv(CMD_FIELD_LEN), byteorder='big')
        if cmd != CMD["GET"]:
            print("GET command not received!")
            return

        # The command is good. Now read and decode the requested
        # filename.
        filename_bytes = connection.recv(Server.RECV_SIZE)
        filename = filename_bytes.decode(MSG_ENCODING)

        # Open the requested file and get set to send it to the
        # client.
        try:
            file = open(filename, 'r').read()
        except FileNotFoundError:
            print(Server.FILE_NOT_FOUND_MSG)
            connection.close()                   
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
            # print("Sent packet bytes: \n", pkt)
            print("Sending file: ", Server.REMOTE_FILE_NAME)
        except socket.error:
            # If the client has closed the connection, close the
            # socket on this end.
            print("Closing client connection ...")
            connection.close()
            return

########################################################################
# CLIENT
########################################################################

class Client:

    RECV_SIZE = 1024
    
    # Define the local file name where the downloaded file will be
    # saved.
    LOCAL_FILE_NAME = "localfile.txt"
    # LOCAL_FILE_NAME = "bee1.jpg"

    def __init__(self):
        

        self.client_CMD = { "SCAN" : 0, "GET" : 1 , "PUT" : 2, "RLIST" : 3, "LLIST" : 4, "CONNECT" : 5, "BYE" : 6}
        self.get_socket() 
        #self.connect_to_server() # this command will be commented out and 
        #                        # replaced in the command handle function

        self.command_handle()
        """
        x, filename = self.command_handle()
        if(x == 0):
            self.scan_command()
        if(x == 1):
            self.get_file(filename)
        if(x == 2):
            self.put_file(filename)
        if(x == 3):
            self.get_fileList()
        if(x == 4):
            self.local_list()
        if(x == 5):
            pass # connect function is still vanilla function
        if(x == 6):
            self.bye_to_server()"""

    def create_udp_socket(self):
        try: 
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            print("UDP Socket Created")
        except Exception as msg:
            print(msg)
            exit()
    
    def discover_service(self):
        print("Attempting to Discover Service")
        try:
            self.udp_socket.sendto(b"SERVICE DISCOVERY", (Server.HOSTNAME, Server.SERVICE_SCAN_PORT))
            msg_bytes, address_port = self.udp_socket.recvfrom(Client.RECV_SIZE)
            print("Received: ", msg_bytes.decode('utf-8'), " IP/Port:", address_port)
        except Exception as msg:
            print(msg)
            exit()
    
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
        while(1):
            
            IP = ""
            port = ""
            filename = ""
            command = input("Command:")
            command_words = self.split_up_string(command)
            print(command_words)
            try:
                x = self.client_CMD[command_words[0].upper()]
            except:
                x = 10000 #arbitrary number not on the commands list
                """
                if(command == 0 or command == 3 or command == 4 or command == 6):
                    return command, ""
                else:
                    filename = input("filename:")
                    return command,filename
            except:
                pass"""
            if(x == 0):
                self.scan_command()
            if(x == 1):
                self.get_file(command_words[1])
            if(x == 2):
                self.put_file(command_words[1])
            if(x == 3):
                self.get_fileList()
            if(x == 4):
                self.local_list()
            if(x == 5):
                self.connect_to_server(command_words[1], command_words[2])
            if(x == 6):
                self.bye_to_server()
    
    def scan_command(self):
        self.create_udp_socket()
        self.discover_service()
        #close udp socket
        self.udp_socket.close()

    def get_file(self, filename):
        print("got in")
        # Create the packet GET field.
        
        get_field = self.client_CMD["GET"].to_bytes(CMD_FIELD_LEN, byteorder='big')

        # Create the packet filename field.
        filename_field = filename.encode(MSG_ENCODING)

        # Create the packet.
        pkt = get_field + filename_field
        print(pkt)
        # Send the request packet to the server.
        self.socket.sendall(pkt)

        # Read the file size field.
        file_size_bytes = self.socket_recv_size(FILE_SIZE_FIELD_LEN)
        if len(file_size_bytes) == 0:
               self.socket.close()
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
                  .format(len(recvd_bytes_total), Client.LOCAL_FILE_NAME))

            with open(Client.LOCAL_FILE_NAME, 'w') as f:
                f.write(recvd_bytes_total.decode(MSG_ENCODING))
        except KeyboardInterrupt:
            print()
            exit(1)
        # If the socket has been closed by the server, break out
        # and close it on this end.
        except socket.error:
            self.socket.close()
    
    def put_file(self, filename):
        # Create the packet GET field.
        get_field = self.client_CMD["PUT"].to_bytes(CMD_FIELD_LEN, byteorder='big')
        # Create the packet
        pkt = get_field + filename.encode(MSG_ENCODING)
        print(pkt)
        # Send the request packet to the server
        self.socket.sendall(pkt)

    
        
    def get_fileList(self):
        # Create the packet GET field.
        get_field = self.client_CMD["RLIST"].to_bytes(CMD_FIELD_LEN, byteorder='big')
        pkt = get_field
        print(pkt)

        # Send the request packet to the server
        self.socket.sendall(pkt)
    
    def local_list(self):
        x = os.listdir()
        for i in range(0,len(x)):
            if x[i][0] != ".":
                print(x[i])
        
    def connect_to_server(self, server_IP, server_port):
        print(server_IP)
        print(server_port)
        try:
            self.socket.connect((str(server_IP), int(server_port)))#((Server.HOSTNAME, Server.PORT))
        except Exception as msg:
            print(msg)
            exit()
    
    def bye_to_server(self):
        try:
            self.socket.close()
        except:
            print("Socket doesn't exist")

    """
    def get_file(self, filename):

        # Create the packet GET field.
        
        get_field = CMD["GET"].to_bytes(CMD_FIELD_LEN, byteorder='big')

        # Create the packet filename field.
        filename_field = filename.encode(MSG_ENCODING)

        # Create the packet.
        pkt = get_field + filename_field
        print(pkt)
        # Send the request packet to the server.
        self.socket.sendall(pkt)

        # Read the file size field.
        file_size_bytes = self.socket_recv_size(FILE_SIZE_FIELD_LEN)
        if len(file_size_bytes) == 0:
               self.socket.close()
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
                  .format(len(recvd_bytes_total), Client.LOCAL_FILE_NAME))

            with open(Client.LOCAL_FILE_NAME, 'w') as f:
                f.write(recvd_bytes_total.decode(MSG_ENCODING))
        except KeyboardInterrupt:
            print()
            exit(1)
        # If the socket has been closed by the server, break out
        # and close it on this end.
        except socket.error:
            self.socket.close()"""
            
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






