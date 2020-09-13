from socket import *
import os
import random
import tcp
import log
from multiprocessing import Process, Lock, Manager

src_port = "DT"
message_number = 1


def handshake(logger, tcpsocket, client_address):
    # Getting SYN
    dst_port = []
    logger.log_this("Awaiting connection...")
    while True:
        try:
            response = tcpsocket.recvfrom(tcp.socket_buffer_size)
            logger.log_this("Received segment from address: <" + str(client_address[0]) + ", " + str(client_address[1]) + ">")
            header_fields, body_response = tcp.process_segment(logger, response[0], 0)
            if header_fields is None:
                continue
            # for word in header_fields:
            # print("Type: " + str(type(word)) + "\tContent: " + str(word))
            if header_fields[2] == 1:
                logger.log_this("SYN received. Starting Handshake protocol...")
                logger.log_this("Destination port identified: " + header_fields[0])
                # Sending SYN + ACK
                seq = 1
                header = tcp.make_tcp_header_words(src_port, header_fields[0], seq, header_fields[2] + 1, tcp.NONE)
                segment = tcp.encode_segment(header, [])
                tcp.send(logger, tcpsocket, client_address, seq + 1, segment, tcp.NONE)

                logger.log_this("Handshake complete. Connection established.")
                break
            else:
                logger.log_this("Rejected connection. SYN not found")
        except timeout:
            pass

    return header_fields[0]


def get_filename(logger, tcpsocket, destiny_port, client_address):
    # Getting SYN
    logger.log_this("Awaiting filename...")
    header_fields, body_response = [], []
    while True:
        try:
            response = tcpsocket.recvfrom(tcp.socket_buffer_size)
            logger.log_this("Received segment from address: <" + str(client_address[0]) + ", " + str(client_address[1]) + ">")
            header_fields, body_response = tcp.process_segment(logger, response[0], 0)
            if header_fields is None:
                continue
            # for word in header_fields:
            # print("Type: " + str(type(word)) + "\tContent: " + str(word))
            #if (header_fields[5] & tcp.PUSH) > 0:
            if header_fields[2] == 50:
                logger.log_this("Data received.")
                # Sending ACK
                seq = 2
                header = tcp.make_tcp_header_words(src_port, destiny_port, seq, header_fields[2] + 1, tcp.ACK)
                segment = tcp.encode_segment(header, [])
                tcp.send_ack(logger, tcpsocket, client_address, segment, 2)
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
    file = open("./ServerFiles/" + filename, "ab")
    search_chunk = 0

    file.write(bytes.fromhex(hex_stream))

    logger.log_this("(Child Process) Saved file successfully")


def get_file(logger, tcpsocket, destiny_port, filename, client_address):
    logger.log_this("Starting file transfer")
    byte_list = Manager().list()
    lock_byte_list = Lock()
    processes = []
    index = 0
    message_number = 50
    file_hex_stream = ""
    expected_seq = 51
    while True:
        try:
            response = tcpsocket.recvfrom(tcp.socket_buffer_size)
            logger.log_this("Received segment from address: <" + str(client_address[0]) + ", " + str(client_address[1]) + ">")
            header_fields, body_response = tcp.process_segment(logger, response[0], 0)
            if header_fields is None:
                continue
            #print("flags: " + hex(header_fields[5]))
            #if (header_fields[5] & tcp.PUSH) > 0:
            if header_fields[2] == expected_seq:
                logger.log_this("Data received. Saving byte stream...")
                # Sending ACK
                header = tcp.make_tcp_header_words(src_port, destiny_port, 0, expected_seq + 1, tcp.NONE)
                segment = tcp.encode_segment(header, [])
                tcp.send_ack(logger, tcpsocket, client_address, segment, message_number)

                if len(body_response) > 0:
                    file_hex_stream += body_response

                # Saving byte stream here and process it. Create a Thread to handle this operation
                #process = Process(target=process_byte_stream, args=[body_response, lock_byte_list, byte_list, index])
                #process.start()
                #processes.append(process)
                index += 1
                message_number += 1
                expected_seq += 1
            if header_fields[2] == 20:
                logger.log_this("File Transfer complete.")
                logger.log_this("FIN received. Terminating connection...")
                seq = 20
                header = tcp.make_tcp_header_words(src_port, destiny_port, seq, 21, tcp.NONE)
                segment = tcp.encode_segment(header, [])
                tcp.send(logger, tcpsocket, client_address, 21, segment, 1)
                break
            else:
                logger.log_this("Rejected segment. ACK received: " + str(header_fields[2]))
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


def end(logger, tcpsocket, destiny_port, client_address):
    while True:
        try:
            response = tcpsocket.recvfrom(tcp.socket_buffer_size)
            logger.log_this("Received segment from address: <" + str(client_address[0]) + ", " + str(client_address[1]) + ">")
            header_fields, body_response = tcp.process_segment(logger, response[0], 0)
            if header_fields is None:
                continue
            # for word in header_fields:
            # print("Type: " + str(type(word)) + "\tContent: " + str(word))
            if (header_fields[5] & tcp.FIN) > 0:

                # Sending SYN + ACK

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
    port = int(input("Provide a valid Port Number:\t"))
    while (port < 0) or (port > 65535): port = int(input("Provide a valid Port Number:\t"))
    address = (host, port)



    # ---------------------------

    # Socket Creation
    logger.log_this("Server is ready. Listening...")
    serversocket = socket(family=AF_INET, type=SOCK_STREAM)

    serversocket.bind(address)
    serversocket.listen()

    tcpsocket, client_address = serversocket.accept()
    tcpsocket.settimeout(tcp.RTT)
    print("Client Address: ")
    print(client_address)

    # --------------------------- HANDSHAKE

    client_port = handshake(logger, tcpsocket, client_address)
    print("Client Port: " + client_port)

    # --------------------------- GET FILE EXTENSION

    filename = get_filename(logger, tcpsocket, client_port, client_address)
    logger.log_this("Filename received: " + filename)

    # --------------------------- SAVING FILE & END CONNECTION

    save_process = get_file(logger, tcpsocket, client_port, filename, client_address)

    # --------------------------- WAITING FOR CHILD PROCESS TO COMPLETE EXECUTION

    save_process.join()
    tcpsocket.close()