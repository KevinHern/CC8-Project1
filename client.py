import socket
import random
import log

bufferSize = 1520
window_size = 0x0001
RTT = 0.150


def client_send(logger, udpsocket, address, message):
    while True:
        udpsocket.sendto(message, address)
        try:
            data, server = udpsocket.recvfrom(1024)
        except socket.timeout:
            logger.log_this("Request Timed Out, resending...")


def do_word(word32, data, bits_to_move):
    return word32 | (data << bits_to_move)

def make_tcp_header_words(dst_port, seq_init, offset, flags, options):
    # SRC and DST Ports
    ports = [ord(c) for c in "KH"] + [ord(c) for c in dst_port]

    # SEQ and ACK Init
    sequence_number = seq_init
    acknowledgment_number = sequence_number + 1

    # Data Offset
    data_offset = offset    # AKA, header's length. Must be multiple of number of 32 bit words

    # Control Flags
    ctrl_flags = b'000000000000' | flags

    # Window Size
    window = window_size

    # Checksum
    checksum = 0

    # Urgent Pointer
    urgent_pointer = 0

    # Options
    options = options

    # Padding
    padding = 0     # Must calculate it here

    # -----------------------------------------------------------------

    # Generating hex encoded header
    header_words = [0x00000000 for i in range(5)]

    # Ports
    for i in range(4):
        header_words[0] = do_word(header_words[0], ports[i] & 0x0000FFFF, 8*(3-i))

    # Sequence Number
    header_words[1] = do_word(header_words[1], sequence_number & 0xFFFFFFFF, 0)

    # Ack Number
    header_words[2] = do_word(header_words[2], acknowledgment_number & 0xFFFFFFFF, 0)

    # Data offset, flags and window size
    header_words[3] = do_word(header_words[3], data_offset & 0x0000000F, 28)
    header_words[3] = do_word(header_words[3], ctrl_flags & 0x00000FFF, 16)
    header_words[3] = do_word(header_words[3], window_size & 0x0000FFFF, 0)

    # Checksum and Urgent Pointer
    header_words[4] = do_word(header_words[4], checksum & 0x0000FFFF, 16)
    header_words[4] = do_word(header_words[4], urgent_pointer & 0x0000FFFF, 0)

    # Options
    totalOptionsLength = 0
    allOptionValues = []
    for option in options:
        totalOptionsLength += option[1]
        if option[1] == 0:
            allOptionValues += [0x00000000]
        elif option[1] == 1:
            allOptionValues += [0x00000001]
        elif option[1] == 2:
            allOptionValues += [0x00000002, 0x00000004, (option[2] & 0x0000FF00) >> 8, (option[2] & 0x000000FF)]
        elif option[1] == 3:
            allOptionValues += [0x00000003, 0x00000003, (option[2] & 0x000000FF)]

    curIndex = 4
    for i in range(len(allOptionValues)):
        if (i % 4) == 0:
            header_words += [0x00000000]
            curIndex +=1
        header_words[curIndex] = do_word(header_words[curIndex], allOptionValues[i], 8*(3-i))

    # Returns in HEX all the words used to construct the header
    return header_words


def make_tcp_body_words(filename):
    pass


def encode_segment(header_words, body_words):
    hex_stream = ""
    all_words = header_words + body_words
    for word in all_words:
        hex_stream += format(word, 'x').upper()
    return hex_stream


def handshake():
    pass


def client_run(logger):
    logger = logger

    # Host (URL/IP)
    host = input("Provide Host:\t")
    # Port Number
    port = input("Provide a valid Port Number:\t")
    if port < 0 or port > 65535: port = input("Provide a valid Port Number:\t")
    address = (host, 12000)

    # ---------------------------

    # Socket Creation
    udpsocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    udpsocket.settimeout(RTT)  # Setting RTT to 150 Milliseconds
    logger.log_this("Client is ready")

    # ---------------------------
