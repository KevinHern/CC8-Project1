from socket import *
import os
import random
import tcp
import log

src_port = "DT"

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

                logger.log_this("Got Filename")
                break
            else:
                logger.log_this("Rejected connection. SYN not found")
        except timeout:
            pass

    # Process the real filename

    return body_response


def end():
    pass


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

    # --------------------------- SAVING FILE

    # --------------------------- END CONNECTION

    end()
