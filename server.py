from socket import *
import os
import random
import tcp
import log
from multiprocessing import Process, Lock, Manager

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
    filename = bytearray.fromhex(body_response).decode()

    return filename


def process_byte_stream(body_response, lock, byte_list, index):
    chunk_bytes = []
    for word in body_response:

        # Checking if word has padding
        byte_length = 0
        if (word & 0x00FFFFFF) == 0:
            byte_length = 1
            word = (word >> 24) & 0x000000FF
        elif (word & 0x0000FFFF) == 0:
            byte_length = 2
            word = (word >> 16) & 0x0000FFFF
        elif (word & 0x000000FF) == 0:
            byte_length = 3
            word = (word >> 8) & 0x00FFFFFF
        else:
            byte_length = 4

        chunk_bytes += [word.to_bytes(length=byte_length, byteorder='big', signed=False)]
        #print("Bytes: " + str(word.to_bytes(length=byte_length, byteorder='big', signed=False)))

    lock.acquire()
    byte_list += [[index, chunk_bytes]]
    lock.release()


def save_file(logger, filename, hex_stream):
    logger.log_this("(Child Process) Saving file...")

    # Creating File
    file = open(filename, "ab")
    search_chunk = 0

    file.write(bytes.fromhex(hex_stream))

    logger.log_this("(Child Process) Saved file successfully")


def get_file(logger, udpsocket, destiny_port, filename):
    logger.log_this("Starting file transfer")
    byte_list = Manager().list()
    lock_byte_list = Lock()
    processes = []
    index = 0
    message_number = 50
    file_hex_stream = ""
    while True:
        try:
            response = udpsocket.recvfrom(tcp.socket_buffer_size)
            address = response[1]
            logger.log_this("Received segment from address: <" + str(address[0]) + ", " + str(address[1]) + ">")
            header_fields, body_response = tcp.process_segment(logger, response[0], 0)
            if header_fields is None:
                continue
            #print("flags: " + hex(header_fields[5]))
            if (header_fields[5] & tcp.PUSH) > 0:
                logger.log_this("Data received. Saving byte stream...")
                # Sending ACK
                seq = 50
                header = tcp.make_tcp_header_words(src_port, destiny_port, seq, header_fields[2] + 1,
                                                   tcp.ACK)
                segment = tcp.encode_segment(header, [])
                tcp.send_ack(logger, udpsocket, address, segment, message_number)

                if len(body_response) > 0:
                    file_hex_stream += body_response

                # Saving byte stream here and process it. Create a Thread to handle this operation
                #process = Process(target=process_byte_stream, args=[body_response, lock_byte_list, byte_list, index])
                #process.start()
                #processes.append(process)
                index += 1
                message_number += 1
            elif header_fields[5] & tcp.FIN:
                logger.log_this("File Transfer complete.")
                break
            else:
                logger.log_this("Rejected segment. PUSH not found")
        except timeout:
            for process in processes:
                process.join()
            break

    # --------------------------- SAVING FILE

    #for process in processes:
    #    process.join()
    #print("File Hex Stream: " + file_hex_stream)
    save_process = Process(target=save_file, args=[logger, filename, file_hex_stream])
    save_process.start()
    return save_process


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

    filename = get_filename(logger, udpsocket, client_port)
    logger.log_this("Filename received: " + filename)

    # --------------------------- SAVING FILE

    save_process = get_file(logger, udpsocket, client_port, filename)

    # --------------------------- END CONNECTION

    end(logger, udpsocket, client_port)

    # --------------------------- WAITING FOR CHILD PROCESS TO COMPLETE EXECUTION

    save_process.join()
