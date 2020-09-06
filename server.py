from socket import *
import os
import random
import tcp
import log

src_port = "DT"

def handshake(logger, udpsocket):
    # Getting SYN
    address, dst_port = [], []
    while True:
        logger.log_this("Accepting connection...")
        response = udpsocket.recvfrom(tcp.socket_buffer_size)
        address = response[1]
        logger.log_this("Received segment from address: <" + str(address[0]) + ", " + str(address[1]) + ">")
        header_response, body_response = tcp.process_segment(logger, response[0], 0)
        if header_response is None:
            continue
        for word in header_response:
            print("Type: " + str(type(word)) + "\tContent: " + str(word))
        if (header_response[5] & tcp.SYN) > 0:
            logger.log_this("SYN received. Starting Handshake protocol...")
            break
        else:
            logger.log_this("Rejected connection. SYN not found")

    # Sending SYN + ACK
    seq = 1
    header = tcp.make_tcp_header_words(src_port, header_response[1], seq, tcp.ACK | tcp.SYN, [])
    segment = tcp.encode_segment(header, [])
    tcp.send(logger, udpsocket, address, seq + 1, segment, 1)

    return address, header_response[1]
    pass


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
    udpsocket.bind((host, port))


    # --------------------------- HANDSHAKE

    client_address, client_port = handshake(logger, udpsocket)

    # --------------------------- GET FILE EXTENSION

    # --------------------------- SAVING FILE

    # --------------------------- END CONNECTION

    end()
