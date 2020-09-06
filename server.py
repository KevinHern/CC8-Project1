from socket import *
import os
import random
import tcp
import log

src_port = "DT"
message_number = 1

def handshake(logger, udpsocket):
    # Getting SYN
    address, dst_port = [], []
    logger.log_this("Awaiting connection...")
    while True:
        try:
            response = udpsocket.recvfrom(tcp.socket_buffer_size)
            address = response[1]
            logger.log_this("Received segment from address: <" + str(address[0]) + ", " + str(address[1]) + ">")
            header_fields, body_response = tcp.process_segment(logger, response[0], 0)
            if header_fields is None:
                continue
            # for word in header_fields:
            # print("Type: " + str(type(word)) + "\tContent: " + str(word))
            if (header_fields[5] & tcp.SYN) > 0:
                logger.log_this("SYN received. Starting Handshake protocol...")
                logger.log_this("Destination port identified: " + header_fields[0])
                # Sending SYN + ACK
                seq = 1
                header = tcp.make_tcp_header_words(src_port, header_fields[0], seq, header_fields[2] + 1,
                                                   tcp.ACK | tcp.SYN)
                segment = tcp.encode_segment(header, [])
                tcp.send(logger, udpsocket, address, seq + 1, segment, 1)

                logger.log_this("Handshake complete. Connection established.")
                break
            else:
                logger.log_this("Rejected connection. SYN not found")
        except timeout:
            pass

    return address, header_fields[1]


def get_filename(logger, udpsocket, destiny_port):
    # Getting SYN
    logger.log_this("Awaiting filename...")
    header_fields, body_response = [], []
    while True:
        try:
            response = udpsocket.recvfrom(tcp.socket_buffer_size)
            address = response[1]
            logger.log_this("Received segment from address: <" + str(address[0]) + ", " + str(address[1]) + ">")
            header_fields, body_response = tcp.process_segment(logger, response[0], 0)
            if header_fields is None:
                continue
            # for word in header_fields:
            # print("Type: " + str(type(word)) + "\tContent: " + str(word))
            if (header_fields[5] & tcp.PUSH) > 0:
                logger.log_this("Data received.")
                # Sending ACK
                seq = 2
                header = tcp.make_tcp_header_words(src_port, destiny_port, seq, header_fields[2] + 1, tcp.ACK)
                segment = tcp.encode_segment(header, [])
                tcp.send_ack(logger, udpsocket, address, segment, 2)
                break
            else:
                logger.log_this("Rejected segment")
        except timeout:
            pass

    # Process the real filename
    filename = ""
    for word in body_response:
        # Checking how much to convert
        chars_to_convert = 0
        if word & 0x00FFFFFF == 0:
            chars_to_convert = 1
        elif word & 0x0000FFFF == 0:
            chars_to_convert = 2
        elif word & 0x000000FF == 0:
            chars_to_convert = 3
        else:
            chars_to_convert = 4

        for i in range(chars_to_convert):
            int_to_char = (word >> (8*(3-i))) & 0x000000FF   # Shift right arithmetic
            filename += chr(int_to_char)
            #print(chr(int_to_char))

    return filename


def save_file(logger, udpsocket, destiny_port, filename):
    # Creating File
    file = open(filename, "w")

    logger.log_this("Starting file transfer")
    while True:
        try:
            response = udpsocket.recvfrom(tcp.socket_buffer_size)
            address = response[1]
            logger.log_this("Received segment from address: <" + str(address[0]) + ", " + str(address[1]) + ">")
            header_fields, body_response = tcp.process_segment(logger, response[0], 0)
            if header_fields is None:
                continue
            if (header_fields[5] & tcp.PUSH) > 0:
                logger.log_this("Data received. Saving byte stream...")
                # Sending ACK
                seq = 50
                header = tcp.make_tcp_header_words(src_port, header_fields[0], seq, header_fields[2] + 1,
                                                   tcp.ACK)
                segment = tcp.encode_segment(header, [])
                tcp.send_ack(logger, udpsocket, address, seq + 1, segment, 1)

                # Saving byte stream here. Create a Thread to handle this operation

            else:
                logger.log_this("Rejected connection. SYN not found")
        except timeout:
            break
    logger.log_this("File Transfer complete.")
    pass


def end(logger, udpsocket, destiny_port):
    while True:
        try:
            response = udpsocket.recvfrom(tcp.socket_buffer_size)
            address = response[1]
            logger.log_this("Received segment from address: <" + str(address[0]) + ", " + str(address[1]) + ">")
            header_fields, body_response = tcp.process_segment(logger, response[0], 0)
            if header_fields is None:
                continue
            # for word in header_fields:
            # print("Type: " + str(type(word)) + "\tContent: " + str(word))
            if (header_fields[5] & tcp.FIN) > 0:
                logger.log_this("FIN received. Terminating connection...")
                # Sending SYN + ACK
                seq = 20
                header = tcp.make_tcp_header_words(src_port, destiny_port, seq, header_fields[2] + 1,
                                                   tcp.ACK | tcp.FIN)
                segment = tcp.encode_segment(header, [])
                tcp.send(logger, udpsocket, address, seq + 1, segment, 1)
                break
            else:
                logger.log_this("Rejected connection. FIN not found")
        except timeout:
            pass

    logger.log_this("Connection terminated successfully")


def server_run(logger):
    logger = logger

    # Host (URL/IP)
    host = "127.0.0.1"
    # Port Number
    #port = int(input("Provide a valid Port Number:\t"))
    port = 8080
    while (port < 0) or (port > 65535): port = int(input("Provide a valid Port Number:\t"))
    address = (host, 12000)

    # ---------------------------

    # Socket Creation
    logger.log_this("Server is ready. Listening...")
    udpsocket = socket(family=AF_INET, type=SOCK_DGRAM)
    udpsocket.settimeout(tcp.RTT)
    udpsocket.bind((host, port))

    # --------------------------- HANDSHAKE

    client_address, client_port = handshake(logger, udpsocket)

    # --------------------------- GET FILE EXTENSION

    response = get_filename(logger, udpsocket, client_port)
    logger.log_this("Filename received: " + response)

    # --------------------------- SAVING FILE



    # --------------------------- END CONNECTION

    end(logger, udpsocket, client_port)
