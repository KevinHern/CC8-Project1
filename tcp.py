from socket import *
import os
import random
import log

socket_buffer_size = 1480       # 1460 bytes from payload + 20 bytes from header
window_size = 0x0001
RTT = 5                         # 5 Seconds of Timeout
const = 0x00000000
FIN = 0x001
SYN = 0x002
PUSH = 0x008
ACK = 0x010
NONE = 0x000
max_segment_length = 740


def process_segment(logger, response, expected_ack):        # Proceso el Stream de hex que he recibido
    # Getting the response and setting auxiliary variables
    response = response.hex().upper()
    total_hexes = len(response)
    hexes_read = 0
    word_count = 0
    segment_words = []
    hexes_to_read = 0
    #print("Received: " + response + "\n")
    #print("Length: " + str(total_hexes) + "\n")

    # The stream is a string of hexes. Time to decode them
    # To make things easier, make chunks of 8 hexes
    #print("Starting to parse hex stream")
    while hexes_read < total_hexes:
        # Setting how many hexes to read.
        # There may be cases that there are less than 8 hexes left to read
        hexes_to_read = 8 if (total_hexes - hexes_read) >= 8 else (total_hexes - hexes_read)

        # Actually reading chunks
        start = 8 * word_count
        new_word = response[start:start + hexes_to_read]
        #print("Hex read: " + new_word)

        # Converting string hex into a number of 32 bits
        new_word = int(new_word, 16) #<< (32 - (4 * hexes_to_read))
        #print("Hexes to read: " + str(hexes_to_read))
        #print("Bits to shift left: " + str(32 - (4 * hexes_to_read)))
        new_word = new_word << (32 - (4 * hexes_to_read))
        #print("Segment hex word: " + hex(new_word))
        segment_words += [new_word]


        # Updating auxiliary variables
        word_count += 1
        hexes_read += hexes_to_read

    # --------------------------------- CHECKSUM

    #print("// All words decoded: ")
    #for x in segment_words:
    #    print(hex(x))

    # Extracting the checksum that is burned in the header of the received segment
    #print("Checksum in header before modification: " + hex(segment_words[4]))
    checksum = (segment_words[4] >> 16) & 0x0000FFFF
    #print("Checksum in header after modification: " + hex(checksum))

    # Setting said checksum to 0.
    # This is done accordingly to the RFC 793 to calculate the checksum on the receiving side
    segment_words[4] = segment_words[4] & 0x0


    # Calculate the checksum
    this_checksum = 0x00000000
    for word in segment_words:
        #print("Extracted word: " + hex(word))
        this_checksum += ((word & 0xFFFF0000) >> 16) + (word & 0x0000FFFF)
    this_checksum = ~this_checksum & 0x0000FFFF

    #print("Header burned checksum: " + hex(checksum))
    #print("Calculated checksum: " + hex(this_checksum))
    if checksum != this_checksum:
        logger.log_this("Checksums do not match, discarding segment.")
        return None, "Checksum"
    


    # --------------------------------- PROCESS SEGMENT

    # Ports
    srcp = chr((segment_words[0] & 0xFF000000) >> 24) + chr((segment_words[0] & 0x00FF0000) >> 16)
    dstp = chr((segment_words[0] & 0x0000FF00) >> 8) + chr((segment_words[0] & 0x000000FF))

    segment_words.pop(0)
    #print("Source: " + srcp + "\nDestiny: " + dstp)

    # Seq & Ack
    sequence = segment_words.pop(0)
    ack = segment_words.pop(0)

    # Offset, flags & window
    offset = (segment_words[0] >> 28) & 0x0000000F
    flags = (segment_words[0] >> 16) & 0x00000FFF
    windows = segment_words.pop(0) & 0x0000FFFF

    #print("Header burned ack: " + hex(expected_ack))
    #print("Expected ACK: " + hex(ack))
    if (expected_ack != ack):
        logger.log_this("Acks do not match, discarding segment. Expected ACK: " + str(expected_ack) + " | Received ACK: " + str(ack))
        return None, "Ack"

    # Urgent pointer
    urgent_pointer = (segment_words.pop(0) & 0x0000FFFF)  # A total of 5 pop operations have been done

    '''
    # Options
    options_words = []
    for i in range(offset - 5):
        options_words += [segment_words.pop(0)]

    options = []
    parsing_completed = 0
    temp_option = []
    for word in options_words:
        must_break = False

        for i in range(4):
            octet = (word >> (8 * (3 - i))) & 0x000000FF
            if octet == 0x00000000:
                parsing_completed = 0
                must_break = True
                break
            elif octet == 0x00000001:
                parsing_completed = 0
            elif octet == 0x00000002:
                parsing_completed = 3
            elif octet == 0x00000003:
                parsing_completed = 2
            else:
                parsing_completed -= 1

            temp_option += [octet]

        if parsing_completed == 0:
            options += [[temp_option]]
            temp_option = []
        if must_break:
            break
    header_words = [srcp, dstp, sequence, ack, offset, flags, windows, checksum, urgent_pointer, options]
    '''
    header_fields = [srcp, dstp, sequence, ack, offset, flags, windows, checksum, urgent_pointer]
    body = response[40:] if len(response) > 40 else ""

    return header_fields, body


def read(logger, udpsocket, address):
    response = udpsocket.recvfrom(socket_buffer_size)
    logger.log_this("Response received from <" + address[0] +", " + str(address[1]) + ">")
    return response


# Just sends and ACK
def send_ack(logger, udpsocket, address, message, message_number):
    #print("Message: ")
    #print(message)
    #print("Message in byte array: ")
    message_array = bytearray.fromhex(message)
    #print(message_array)
    #print("Length of Byte array: " + str(len(message_array)))
    udpsocket.sendto(bytearray.fromhex(message), address)
    logger.log_this("TCP ACK #" + str(message_number) + " sent...")


# Send the hex stream AND expect an ACK
def send(logger, udpsocket, address, expected_ack, message, message_number):
    #print("Message: ")
    #print(message)
    #print("Message in byte array: ")
    message_array = bytearray.fromhex(message)
    #print(message_array)
    #print("Length of Byte array: " + str(len(message_array)))
    while True:
        udpsocket.sendto(message_array, address)
        logger.log_this("TCP segment #" + str(message_number) + " sent...")
        try:
            # Received TCP segment
            response = read(logger, udpsocket, address)
            #print("(response) Received: ")
            #print(response)

            # Processing
            header_words, body_words = process_segment(logger, response[0], expected_ack)

            # Resend if ack or checksum does not match
            if header_words is None:
                logger.log_this(body_words + " does not match: Sent ACK: " + str(expected_ack) +
                                " | Received ACK: " + str(make_tcp_header_words([3])) + ". Resending")
                continue
            else:
                return header_words, body_words

        except timeout:
            logger.log_this("Request Timed Out, resending...")


# Corrimiento de bits
def do_word(word32, data, bits_to_move):
    return word32 | (data << bits_to_move)


# Hacer el header del TCP
# Devuelve: Una lista con todas las palabras del header en hex.
def make_tcp_header_words(src_port, dst_port, seq_number, ack_number, flags):
    # Generating hex encoded header
    header_words = [0x00000000 for i in range(5)]

    # -----------------------------------------------

    #print("\n//----- CREANDO HEADER -----//\n")
    # SRC and DST Ports
    #print("\n//----- PUERTOS -----//\n")
    #print("SRC: " + src_port + "\t|\tDST: " + dst_port)
    ports = [ord(c) for c in src_port] + [ord(c) for c in dst_port]
    #print("// Ports Integer encoding: ")
    #print(ports)
    #print("// Ports Hex Encoding: ")
    #for x in ports:
    #    print(hex(x))

    for i in range(4):
        header_words[0] = do_word(header_words[0], ports[i] & 0x0000FFFF, 8 * (3 - i))

    #print("// Primer Word del header:")
    #print(hex(header_words[0]))

    #print("\n//----- SEQUENCE -----//\n")
    sequence_number = seq_number
    header_words[1] = do_word(header_words[1], sequence_number & 0xFFFFFFFF, 0)
    #print("// Sequence Number: " + str(sequence_number))
    #print("// Hex Sequence Number: " + hex(sequence_number))
    #print("// Segundo Word del header: " + hex(header_words[1]))

    #print("\n//----- ACK -----//\n")
    # Ack Number
    acknowledgment_number = ack_number
    header_words[2] = do_word(header_words[2], acknowledgment_number & 0xFFFFFFFF, 0)
    #print("// Acknowledgment Number: " + str(acknowledgment_number))
    #print("// Hex Acknowledgment Number: " + hex(acknowledgment_number))
    #print("// Tercer Word del header: " + hex(header_words[2]))

    #print("\n//----- RESERVED, CONTROL FLAGS & WINDOW SIZE -----//\n")

    header_words[3] = 0x00000000

    # Data Offset
    #data_offset = 5
    #print("// Data Offset Number: " + str(data_offset))
    #print("// Hex Data Offset Number: " + hex(data_offset))

    # Control Flags
    #ctrl_flags = 0x000 | flags
    #print("// Control Flags: " + str(ctrl_flags))
    #print("// Hex Control Flags: " + hex(ctrl_flags))

    # Window Size
    #window = 0
    #print("// Window Size: " + str(window_size))
    #print("// Hex Window Size: " + hex(window_size))

    # Data offset, flags and window size
    #header_words[3] = do_word(header_words[3], data_offset & 0x0000000F, 28)
    #header_words[3] = do_word(header_words[3], ctrl_flags & 0x00000FFF, 16)
    #header_words[3] = do_word(header_words[3], window_size & 0x0000FFFF, 0)
    #print("// Cuarto Word del header: " + hex(header_words[3]))

    #print("\n//----- CHECKSUM Y URGENT POINTER -----//\n")
    # Checksum
    # Initialize Checksum to 0. It is calculated when we have both the header and the body hexes
    # Specific calculation point: encode_segment()
    checksum = 0
    #print("// Checksum Size: " + str(checksum))
    #print("// Hex Checksum Size: " + hex(checksum))

    # Urgent Pointer
    urgent_pointer = 0
    #print("// Urgent Pointer Size: " + str(urgent_pointer))
    #print("// Hex Urgent Pointer Size: " + hex(urgent_pointer))

    header_words[4] = do_word(header_words[4], checksum & 0x0000FFFF, 16)
    header_words[4] = do_word(header_words[4], urgent_pointer & 0x0000FFFF, 0)
    #print("// Quinto Word del header: " + hex(header_words[4]))

    # Returns in HEX all the words used to construct the header
    return header_words

# Here we encode all the 32 bit words hexes into a single string (header and body)
# Note that there may be cases you have to add 0 to complete the 32 bit words.
# Example: convert 0x2C
# Adding the corresponding 0s to the string to complete the word would look like this:
# 0x0000002C


def encode_segment(header_words, body_words):

    # ---------------------------- ENCODE BODY SEGMENTS

    # Encode everything else.
    body_stream = ""

    # Last word is problematic, do different analysis
    copy_body_words = body_words.copy()
    last_word = ""
    if len(copy_body_words) > 0:
        last_word = copy_body_words.pop(-1)
        total_hex = 0
        if (last_word & 0x00FFFFFF) == 0:
            total_hex = 2
            last_word = (last_word >> 24) & 0x000000FF
        elif (last_word & 0x0000FFFF) == 0:
            total_hex = 4
            last_word = (last_word >> 16) & 0x0000FFFF
        elif (last_word & 0x000000FF) == 0:
            total_hex = 6
            last_word = (last_word >> 8) & 0x00FFFFFF
        else:
            total_hex = 8

        last_word = format(last_word, 'x').upper()
        last_word = ('0' * (total_hex - len(last_word))) + last_word

    for word in copy_body_words:
        hex_word = format(word, 'x').upper()

        if len(hex_word) < 8:
            for i in range(8 - len(hex_word)):
                hex_word = "0" + hex_word

        body_stream += hex_word

    body_stream = body_stream + last_word
    content_length = 700 if len(body_stream) >= 700 else len(body_stream)

    # ----------------------- ENCODE HEADER

    # Encode header segment
    header_words[3] = do_word(header_words[3], content_length & 0x0000FFFF, 0)

    all_words = header_words + body_words


    # Calculate checksum
    checksum = 0x00000000
    for word in all_words:
        checksum += ((word & 0xFFFF0000) >> 16) + (word & 0x0000FFFF)
    checksum = (~checksum << 16) & 0xFFFF0000
    
    #print("// Calculated Checksum before sending: " + hex(checksum))

    header_words[4] = do_word(header_words[4], checksum, 0)



    #print("// All words before sending:")
    #for word in all_words:
        #print(hex(word))

    head_stream = ""
    for word in header_words:
        hex_word = format(word, 'x').upper()
        # print("Hex Word to Encode: " + hex_word)
        # Adding 0s to the string
        if len(hex_word) < 8:
            for i in range(8 - len(hex_word)):
                hex_word = "0" + hex_word
        # print("Hex Word Encoded: " + hex_word)
        head_stream += hex_word

    stream = head_stream + body_stream

    #print("\n//----- Hex stream a enviar -----//")
    #print(stream)
    stream = stream[0:max_segment_length] if len(stream) > 740 else stream

    return stream
