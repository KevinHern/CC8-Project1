from socket import *
import os
import random
import log
import tcp

src_port = "KH"

def make_file_words(filename):
    body_words = []
    if filename is not None:
        batch_size = 4  # Read in chunks of 32 bit words
        with open(filename, "rb") as file:
            while True:
                piece = file.read(batch_size)
                if piece == b'':
                    break

                body_words += [int(piece.hex(), 16)]

            file.close()

            '''
            file_size = os.path.getsize(filename)
            bytes_read = 0
            batch_size = 1460  # 1460 Bytes
            while bytes_read < file_size:
                bytes_to_read = batch_size if (bytes_read + batch_size) < file_size else file_size - bytes_read
                piece = file.read(bytes_to_read)
                print(piece)

                bytes_read += bytes_to_read

            '''
    return body_words





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
        if option > 5 or option < 1:
            print("Select a valid option")
            continue
        else:
            filename_to_send = files[i]
            logger.log_this("Selected " + files[i] + " to send.")
            break

    # ----------------------- SEND FILENAME

    seq = 50
    header = tcp.make_tcp_header_words(src_port, destiny_port, seq, 0, tcp.PUSH)
    segment = tcp.encode_segment(header, [])

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


def end(seq):
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
    send_file_extension(logger, udpsocket, dst_port, address, file_list)


    # --------------------------- READ FILE

    '''
    file_words = []
    while True:
        try:
            filename = input("Provide the file name:\t")
            file_words = make_file_words(filename)
            logger.log_this("Reading and processing <" + filename + ">")
            break
        except:
            logger.log_this("File not found <" + filename + ">")

    tcp_body_segments = []
    while len(file_words) > 0:
        words_to_extract = 1460 if len(file_words) >= 1460 else len(file_words)
        temp_list = []
        for i in range(words_to_extract):
            temp_list += [file_words.pop(0)]
        tcp_body_segments += [temp_list]

    # --------------------------- SEND FILE

    sequence = 100
    options = []
    segment_number = 1
    for segment_body_words in tcp_body_segments:
        segment_header_words = make_tcp_header_words("DT", sequence, len(options) + 5, 0x00000000, options)
        segment = encode_segment(segment_header_words, segment_body_words)
        # Send here
        client_send(logger, udpsocket, address, sequence + 1, segment, segment_number)
        sequence += + 1
        segment_number += 1

    # --------------------------- END CONNECTION
    
    '''

    end_seq = random.randint(500,1000)
    end(end_seq)
