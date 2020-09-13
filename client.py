from socket import *
import os
import random
import log
import tcp

src_port = "KH"
message_number = 1
max_body_length = 700


def make_body_segment(hex_file_stream):
    words = []
    word_count = 0
    hexes_to_read = max_body_length if len(hex_file_stream) >= max_body_length else len(hex_file_stream)

    hex_stream_to_read = hex_file_stream[0:hexes_to_read]
    residual_hex_stream = hex_file_stream[hexes_to_read:]

    # The stream is a string of hexes. Time to decode them
    # To make things easier, make chunks of 8 hexes
    while hexes_to_read > 0:
        # Actually reading chunks

        hex_read = 8 if hexes_to_read >= 8 else hexes_to_read

        start = 8 * word_count
        new_word = hex_stream_to_read[start:start + hex_read]
        #print("Hex read: " + str(hex_read))
        #print("Hex fragment: " + new_word)

        # Converting string hex into a number of 32 bits
        new_word = int(new_word, 16) << (32 - (4 * hex_read))
        #print("Transformed Hex fragment: " + hex(new_word))

        words += [new_word]

        # Updating auxiliary variables
        word_count += 1
        hexes_to_read -= 8
    #print("Old")
    return residual_hex_stream, words


# Extract the filename's bytes, then read chunks of 730 bytes.
# Then for each chunk, all the 32 bit words are made
# TL;DR: Get filename, return each body segment to send
def make_file_hex_stream(filename):
    hex_file_stream = ""
    if filename is not None:
        batch_size = 2048  # Read in chunks of 4 bytes (aka, 32 bit words)
        with open("./files/" + filename, "rb") as file:
            arr = bytearray()
            while True:
                piece = file.read(batch_size)   # Read a word
                if piece == b'':
                    break

                arr.extend(piece)

            #print("Byte Array: ")
            #print(arr)
            hex_file_stream = arr.hex()
            #print("As Hex Stream: " + hex_file_stream)
            file.close()
    return hex_file_stream


def handshake(logger, udpsocket, address):
    # Send SYN
    logger.log_this("Establishing connection...")
    logger.log_this("Starting 3 way Handshake")
    seq = 1
    header = tcp.make_tcp_header_words(src_port, "--", seq, 0, tcp.SYN)
    #print(header)
    segment = tcp.encode_segment(header, [])

    # Send and get ACK + SYN
    header_fields, body_response = [], []
    while True:
        logger.log_this("Sending SYN. SEQ = " + str(seq) + ". Expected ACK: " + str(seq+1))
        header_fields, body_response = tcp.send(logger, udpsocket, address, seq+1, segment, tcp.NONE)
        #if (header_fields[5] & (tcp.ACK | tcp.SYN)) > 0 and ((seq + 1) == header_fields[3]):
        if (header_fields[2] == 1) and (header_fields[3] == 2):
            logger.log_this("ACK Received. Destination port identified: " + header_fields[0])
            break
        else:
            logger.log_this("Received a wrong response, resending")

    # Send ACK
    seq += 1
    header = tcp.make_tcp_header_words(src_port, header_fields[0], seq, header_fields[2] + 1, tcp.ACK)
    segment = tcp.encode_segment(header, [])

    # Probably should make a new loop in case the server does not receive the ACK... eh
    logger.log_this("Enviando ACK. SEQ =" + str(seq))
    tcp.send_ack(logger, udpsocket, address, segment, tcp.NONE)

    logger.log_this("Handshake complete. Connection established.")
    return header_fields[0]


def send_file_extension(logger, tcpsocket, destiny_port, address, files):
    # ------------------------ ASK FILE

    print("Select what file to send")
    for i in range(len(files)):
        print(str(i+1) + ".\t" + files[i])

    filename_to_send = ""
    while True:
        option = int(input("Your option: \t"))
        if option < 1 or option > len(files):
            print("Select a valid option")
            continue
        else:
            filename_to_send = files[option-1]
            logger.log_this("Selected " + files[option-1] + " to send.")
            break

    # Encoding filename
    filename_chars = [ord(c) for c in filename_to_send]
    #print(filename_chars)
    num_body_words = (len(filename_chars)//4) + (1 if len(filename_chars)%4 > 0 else 0)
    body_words = []
    for i in range(num_body_words):
        body_words += [0x00000000]
        for j in range(4):
            if len(filename_chars) == 0:
                break
            body_words[i] = tcp.do_word(body_words[i], filename_chars.pop(0) & 0x000000FF, 8 * (3 - j))

    #print("Encoded filename: ")
    #print(body_words)

    # ----------------------- SEND FILENAME

    seq = 50
    header = tcp.make_tcp_header_words(src_port, destiny_port, seq, 0, tcp.PUSH)
    segment = tcp.encode_segment(header, body_words)

    # Send and get ACK
    header_fields, body_response = [], []
    while True:
        logger.log_this("Sending filename: '" + filename_to_send + "'. SEQ = " + str(seq) + ". Expected ACK: " + str(seq + 1))
        header_fields, body_response = tcp.send(logger, tcpsocket, address, seq + 1, segment, tcp.NONE)
        if header_fields[3] == 51:
            logger.log_this("ACK Received. Proceeding to sending the file contents.")
            break
        else:
            logger.log_this("Received wrong ACK: " + str(header_fields[3]) + ", resending")
    return filename_to_send


def end(logger, tcpsocket, destiny_port, address):
    logger.log_this("Terminating connection...")

    seq = 20
    header = tcp.make_tcp_header_words(src_port, destiny_port, seq, 0, tcp.FIN)
    # print(header)
    segment = tcp.encode_segment(header, [])

    # Send and get ACK + FIN
    header_fields, body_response = [], []
    while True:
        logger.log_this("Sending FIN. SEQ = " + str(seq) + ". Expected ACK: " + str(seq + 1))
        header_fields, body_response = tcp.send(logger, tcpsocket, address, seq + 1, segment, tcp.NONE)
        #if ((header_fields[5] & (tcp.ACK | tcp.FIN)) > 0) and ((seq + 1) == header_fields[3]):
        if 21 == header_fields[3]:
            logger.log_this("ACK Received. Sever terminating connection too")
            # Send ACK
            seq += 1
            header = tcp.make_tcp_header_words(src_port, destiny_port, seq, header_fields[2] + 1, tcp.NONE)
            segment = tcp.encode_segment(header, [])

            # Probably should make a new loop in case the server does not receive the ACK... eh
            logger.log_this("Enviando ACK. SEQ =" + str(seq))
            tcp.send_ack(logger, tcpsocket, address, segment, 2)
            break
        else:
            logger.log_this("Received wrong ACK: " + str(header_fields[3]) + ", resending")


    logger.log_this("Connection terminated successfully...")
    pass


def client_run(logger):
    logger = logger

    # Host (URL/IP)
    host = input("Provide Host:\t")
    #host = "127.0.0.1"
    # Port Number
    port = int(input("Provide a valid Port Number:\t"))
    #port = 8080
    while (port < 0) or (port > 65535): port = int(input("Provide a valid Port Number:\t"))
    address = (host, port)

    # ---------------------------

    # Socket Creation
    tcpsocket = socket(family=AF_INET, type=SOCK_STREAM)
    tcpsocket.connect(address)
    tcpsocket.settimeout(tcp.RTT)
    logger.log_this("Client is ready")

    # --------------------------- HANDSHAKE

    dst_port = handshake(logger, tcpsocket, address)


    # --------------------------- SEND FILE EXTENSION
    # Ask what file to send
    file_list = ["test.txt", "5KB.txt", "500B.jpg", "1KB.jpg", "2KB.jpg", "5KB.jpg", "Pew.mp3", "genial.png"]
    filename = send_file_extension(logger, tcpsocket, dst_port, address, file_list)

    # --------------------------- READ FILE

    logger.log_this("Reading file: " + filename)
    stream_to_send = make_file_hex_stream(filename)  # Get all the file encoded in 32 bit words

    # --------------------------- SEND FILE

    sequence = 51
    segment_number = 1
    logger.log_this("Starting file transfer...")

    while len(stream_to_send) > 0:
        # Make body segments here
        stream_to_send, body_words = make_body_segment(stream_to_send)

        # Create header
        segment_header_words = tcp.make_tcp_header_words(src_port, dst_port, sequence, 0, tcp.NONE)
        segment = tcp.encode_segment(segment_header_words, body_words)

        # Send here
        tcp.send(logger, tcpsocket, address, sequence + 1, segment, segment_number)
        sequence += + 1
        segment_number += 1

    logger.log_this("Transfer done")
    # --------------------------- END CONNECTION

    end(logger, tcpsocket, dst_port, address)
    tcpsocket.close()
