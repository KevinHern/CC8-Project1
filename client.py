from socket import *
import os
import random
import log
import tcp

src_port = "KH"
message_number = 1


def hex_stream_to_32words(hex_stream):
    total_hexes = len(hex_stream)
    hexes_read = 0
    words = []
    word_count = 0
    hexes_to_read = 0

    # The stream is a string of hexes. Time to decode them
    # To make things easier, make chunks of 8 hexes
    while hexes_read < total_hexes:
        # Setting how many hexes to read.
        # There may be cases that there are less than 8 hexes left to read
        hexes_to_read = 8 if (total_hexes - hexes_read) >= 8 else (total_hexes - hexes_read)

        # Actually reading chunks
        start = 8 * word_count
        new_word = hex_stream[start:start + hexes_to_read]

        # Converting string hex into a number of 32 bits
        new_word = int(new_word, 16)  # << (32 - (4 * hexes_to_read))
        new_word = new_word << (32 - (4 * hexes_to_read))
        words += [new_word]

        # Updating auxiliary variables
        word_count += 1
        hexes_read += hexes_to_read

    '''
    print("Received hex stream: " + hex_stream)
    for word in words:
        print("Hex word: " + format(word, 'x').upper())
    '''
    return [words]


# Extract the filename's bytes, then read chunks of 730 bytes.
# Then for each chunk, all the 32 bit words are made
# TL;DR: Get filename, return each body segment to send
def make_file_segments(filename):
    body_segments = []
    if filename is not None:
        batch_size = 730  # Read in chunks of 730 bit words
        with open(filename, "rb") as file:
            while True:
                piece = file.read(batch_size)
                if piece == b'':
                    break

                hex_stream = int(piece.hex(), 16)
                body_segments += hex_stream_to_32words(format(hex_stream, 'x').upper())

            file.close()
    return body_segments


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
        header_fields, body_response = tcp.send(logger, udpsocket, address, seq+1, segment, 1)
        if (header_fields[5] & (tcp.ACK | tcp.SYN)) > 0 and ((seq + 1) == header_fields[3]):
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
    tcp.send_ack(logger, udpsocket, address, segment, 2)

    logger.log_this("Handshake complete. Connection established.")
    return header_fields[1]


def send_file_extension(logger, udpsocket, destiny_port, address, files):
    # ------------------------ ASK FILE

    print("Select what file to send")
    for i in range(len(files)):
        print(str(i+1) + ".\t" + files[i])

    filename_to_send = ""
    while True:
        option = int(input("Your option: \t"))
        if option > 4 or option < 1:
            print("Select a valid option")
            continue
        else:
            filename_to_send = files[option-1]
            logger.log_this("Selected " + files[option-1] + " to send.")
            break

    # Encoding filename
    filename_chars = [ord(c) for c in filename_to_send]
    print(filename_chars)
    num_body_words = (len(filename_chars)//4) + (1 if len(filename_chars)%4 > 0 else 0)
    body_words = []
    for i in range(num_body_words):
        body_words += [0x00000000]
        for j in range(4):
            if len(filename_chars) == 0:
                break
            body_words[i] = tcp.do_word(body_words[i], filename_chars.pop(0) & 0x000000FF, 8 * (3 - j))

    print("Encoded filename: ")
    print(body_words)

    # ----------------------- SEND FILENAME

    seq = 50
    header = tcp.make_tcp_header_words(src_port, destiny_port, seq, 0, tcp.PUSH)
    segment = tcp.encode_segment(header, body_words)

    # Send and get ACK
    header_fields, body_response = [], []
    while True:
        logger.log_this("Sending filename: '" + filename_to_send + "'. SEQ = " + str(seq) + ". Expected ACK: " + str(seq + 1))
        header_fields, body_response = tcp.send(logger, udpsocket, address, seq + 1, segment, 3)
        if (header_fields[5] & tcp.ACK) > 0 and ((seq + 1) == header_fields[3]):
            logger.log_this("ACK Received. Proceeding to sending the file contents.")
            break
        else:
            logger.log_this("Received a wrong response, resending")
    return filename_to_send


def end(logger, udpsocket, destiny_port, address):
    logger.log_this("Terminating connection...")

    seq = 20
    header = tcp.make_tcp_header_words(src_port, destiny_port, seq, 0, tcp.FIN)
    # print(header)
    segment = tcp.encode_segment(header, [])

    # Send and get ACK + FIN
    header_fields, body_response = [], []
    while True:
        logger.log_this("Sending FIN. SEQ = " + str(seq) + ". Expected ACK: " + str(seq + 1))
        header_fields, body_response = tcp.send(logger, udpsocket, address, seq + 1, segment, 1)
        if ((header_fields[5] & (tcp.ACK | tcp.FIN)) > 0) and ((seq + 1) == header_fields[3]):
            logger.log_this("ACK Received. Sever terminating connection too")
            # Send ACK
            seq += 1
            header = tcp.make_tcp_header_words(src_port, destiny_port, seq, header_fields[2] + 1, tcp.ACK)
            segment = tcp.encode_segment(header, [])

            # Probably should make a new loop in case the server does not receive the ACK... eh
            logger.log_this("Enviando ACK. SEQ =" + str(seq))
            tcp.send_ack(logger, udpsocket, address, segment, 2)
            break
        else:
            logger.log_this("Received a wrong response, resending")


    logger.log_this("Connection terminated successfully...")
    pass


def client_run(logger):
    logger = logger

    # Host (URL/IP)
    #host = input("Provide Host:\t")
    host = "127.0.0.1"
    # Port Number
    #port = int(input("Provide a valid Port Number:\t"))
    port = 8080
    while (port < 0) or (port > 65535): port = int(input("Provide a valid Port Number:\t"))
    address = (host, port)

    # ---------------------------

    # Socket Creation
    udpsocket = socket(family=AF_INET, type=SOCK_DGRAM)
    udpsocket.settimeout(tcp.RTT)
    logger.log_this("Client is ready")

    # --------------------------- HANDSHAKE

    dst_port = handshake(logger, udpsocket, address)

    # --------------------------- SEND FILE EXTENSION
    # Ask what file to send
    file_list = ["test.txt", "hola.java", "sonido.mp3", "genial.png"]
    filename = send_file_extension(logger, udpsocket, dst_port, address, file_list)

    # --------------------------- READ FILE

    logger.log_this("Reading file: " + filename)
    body_segments = make_file_segments(filename)  # Basically, the total amount of tcp segments to send

    # --------------------------- SEND FILE

    sequence = 51
    segment_number = 4
    logger.log_this("Starting file transfer...")
    for body_segment in body_segments:
        segment_header_words = tcp.make_tcp_header_words(src_port, dst_port, sequence, tcp.PUSH)
        segment = tcp.encode_segment(segment_header_words, body_segment)
        # Send here
        tcp.send(logger, udpsocket, address, sequence + 1, segment, segment_number)
        sequence += + 1
        segment_number += 1

    logger.log_this("Transfer done")
    # --------------------------- END CONNECTION

    end(logger, udpsocket, dst_port, address)
