#!/usr/bin/python

# Network mode library with all required functions
# to run NRF24L01 transceiver over Raspberry Pi and
# communicate with others using TDM-type approach.

# Brian Lavery's lib_nrf24.py library is used for
# Raspberry Pi and "Virtual GPIO" configuration

# MTP Team C. Fall 2017-18. ETSETB, Universitat Politecnica de Catalunya (UPC).




#### Required libraries ####
import sys
import time
import random
from lib_nrf24 import NRF24
import RPi.GPIO as GPIO
import spidev
from math import *
import os.path



#### Network parameters ####
RF_CH = 0x64                                # UL & DL channels
TX_CMPLT = RX_CMPLT = 0                     # Completed files
PWR_LVL = NRF24.PA_MIN                      # Transceiver output (HIGH = -6 dBm + 20 dB)
BRATE = NRF24.BR_250KBPS                    # 250 kbps bit rate
TDATA = TACK =  0.2                         # Data and ACK frames timeout (in seconds)
TCTRL = TINIT = 0                           # Control frame and initialization random timeouts (in seconds)
TMAX = 120                                  # Max time for network mode (in seconds)
PLOAD_SIZE = 32                             # Payload size corresponding to data in one frame (32 B max)
HDR_SIZE = 1                                # Header size inside payload frame
PIPE_TX = [0xc2, 0xc2, 0xc2, 0xc2, 0xc2]    # TX pipe address
PIPE_RX = [0xc2, 0xc2, 0xc2, 0xc2, 0xc2]    # RX pipe address
GPIO_TX = 22                                # TX transceiver's CE to Raspberry GPIO
GPIO_RX = 23                                # RX transceiver's CE to Raspberry GPIO
WAITING_DATA = False                        # Flag to know whether data frame is expected or control, otherwise
SEND_CTRL = False                           # Flag to know if control frame must be sent
TEAM_A = 0
TEAM_B = 1
TEAM_C = 2
TEAM_D = 3
MY_TEAM = TEAM_C
TX = MY_TEAM                                # TX for current time slot
NEXT = TEAM_D                               # TX for next time slot
TX_POS = [0,0,0,0]
RX_POS = [0,0,0,0]
TX_ACK = [0,0,0,0]
RX_ACK = [0,0,0,0]
POS_MAX = 17



#### Radio interfaces ####
radio_Tx = NRF24(GPIO, spidev.SpiDev())
radio_Rx = NRF24(GPIO, spidev.SpiDev())
#radio_Rx = radio_Tx = 0



#### Class and function definitions ####

# COMMS initialization
# Input:  None
# Output: OK (0) or ErrNum (-1)
def init_comms():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(GPIO_RX, GPIO.OUT)
    GPIO.output(GPIO_RX,GPIO.LOW)
    GPIO.setup(GPIO_TX, GPIO.OUT)
    GPIO.output(GPIO_TX,GPIO.LOW)

    # Enable transceivers with CE connected to GPIO_TX (22) and GPIO_RX (23)
    radio_Tx.begin(0, GPIO_TX)
    radio_Rx.begin(1, GPIO_RX)

    # Payload Size set to defined value
    radio_Tx.setPayloadSize(PLOAD_SIZE)
    radio_Rx.setPayloadSize(PLOAD_SIZE)

    # We choose the channels to be used for one and the other transceiver
    radio_Tx.setChannel(RF_CH)
    radio_Rx.setChannel(RF_CH)

    # Transmission Rate
    radio_Tx.setDataRate(BRATE)
    radio_Rx.setDataRate(BRATE)

    # Configuration of the power level to be used by the transceiver
    radio_Tx.setPALevel(PWR_LVL)
    radio_Rx.setPALevel(PWR_LVL)

    # Disabled Auto Acknowledgement
    radio_Tx.setAutoAck(False)
    radio_Rx.setAutoAck(False)

    # Enable CRC 16b
    radio_Tx.setCRCLength(NRF24.CRC_16)
    radio_Tx.setCRCLength(NRF24.CRC_16)

    # Dynamic payload size
    radio_Tx.enableDynamicPayloads()
    radio_Rx.enableDynamicPayloads()

    # Open the writing and reading pipe
    radio_Tx.openWritingPipe(PIPE_TX)
    radio_Rx.openReadingPipe(3, PIPE_RX)

    print("Transmitter Details #################################################################################")
    radio_Tx.printDetails()
    print("*---------------------------------------------------------------------------------------------------*")
    print("Receiver Details ####################################################################################")
    radio_Rx.printDetails()
    print("*---------------------------------------------------------------------------------------------------*")

    return 0


# Network mode.
# Input:  None
# Output: OK (0) or ErrNum (-1)
def network_main():
    random.seed(int(time.time()))
    TINIT = random.uniform(5,10)

    # Start timer
    start_time = time.time()

    while(not radio_Rx.available(0) and time.time() < (start_time + TINIT)):
        # time.sleep(0.2)
        pass

    if(not radio_Rx.available(0)):
        SEND_CTRL = True

    while(TX_CMPLT < 3 and RX_CMPLT < 3 and time.time() < (start_time + TMAX)):
        if SEND_CTRL:
            # Send control (maybe TINIT or TCTRL)
            packet = PKT()
            packet.generate_pkt(0)
            packet.send_pkt()

            # Wait for ACKs
            if(received_acks()):
                # 2 or 3 ACKs received.
                send_data()

            # else:
            #     # Timeout (less than 2 ACKs), wait control.
            #     pass
            
            SEND_CTRL = False

        else:
            if(WAITING_DATA):
                # Data frame to be received
                packet = PKT()
                if(received_data()):
                    # Data received
                    # ACK = 1 for TX data
                    RX_ACK[TX] = 1

                else:
                    # Timeout TDATA
                    # ACK = 0 for TX data
                    RX_ACK[TX] = 0

                WAITING_DATA = False
                if(i_am_next()):
                    TX = MY_TEAM
                    NEXT = TEAM_D
                    SEND_CTRL = True

                else:
                    SEND_CTRL = False


            else:
                # Control frame to be received
                rx_ctrl, packet = received_ctrl()
                if(rx_ctrl):
                    # Control received. TX and NEXT updated.
                    t_send_ack = random.uniform(0,0.01)
                    time.sleep(t_send_ack)
                    # Send ACK
                    send_ack(packet)
                    WAITING_DATA = True

                else:
                    # Timeout
                    TX = MY_TEAM
                    NEXT = TEAM_D
                    SEND_CTRL = True


    return 0


# Packet class type. It includes:
#       - Type: control (0) or data (1) (int)
#       - Header: flags and identifiers before payload (chr)
#       - Payload: packet data (string)
#       - Payload Length: int with total length of payload (int in B)
#       - Frame Data: header+payload (chr list)
class PKT:
    def __init__(self, typ=0,header=0,payload=""):
        self.typ = typ
        self.header = header
        self.payload = payload
        self.payloadLength = len(payload)
        self.frameData = list(chr(self.header)+self.payload)


    # Given a payload dataset, the packet is arranged to be conformed to standard definitions.
    # Input:
    #       - Type: Control (0) or Data (1)
    #       - RX_ID: Only for data packets, receiver ID
    #       - Payload: Bytes corresponding to data, (ACKs for control or file data)
    # Output: OK (0) or ErrNum. Generated packet (of size PLOAD_SIZE), corresponding to transceiver's frame payload field
    def generate_pkt(self, typ, payload="", rx_id=0):
        if typ:
            # Data packet
            # Header = 1 + RX_ID + TX_POS(RX_ID)
            if (rx_id == MY_TEAM or rx_id > 3):
                return -1

            else:
                if len(payload) > (PLOAD_SIZE-HDR_SIZE):
                    return -2
                else:
                    self.typ = typ
                    self.header = chr(128+(rx_id<<5)+TX_POS(rx_id))
                    self.payload = payload
                    self.payloadLength = len(payload)
                    self.frameData = list(self.header+self.payload)   
                    return 0

        else:
            # Control packet
            # Header = 0 + MY_TEAM_ID + NEXT_ID + 000 (Reserved flags); NEXT previously updated.
            # Payload = ACK0+ACK1+ACK2 (1B each)
            self.typ = typ
            self.header = chr(0+(MY_TEAM<<5)+(NEXT<<3)+(RX_ACK[0]<<2)+(RX_ACK[1]<<1)+RX_ACK[2])
            self.payload = ""
            self.payloadLength = 0
            self.frameData = list(self.header)
            return 0


    # Read input packet from RF interface
    # Input:  None
    # Output: OK (0) or ErrNum. Received packet (self), corresponding to transceiver's frame payload field
    def read_pkt(self):
        self.frameData = []
        radio_Rx.read(self.frameData, radio_Rx.getDynamicPayloadSize())

        if(len(self.frameData) < 1):
            # Empty frame
            return -1

        else:
            self.header = ord(self.frameData[0])
            if(self.header < 128):
                # Control packet
                if(WAITING_DATA):
                    return -2
                else:
                    self.typ = 0
                    # if(self.is_ACK()):
                    #     # ACK to MY_TEAM
                    #     # Doing nothing here, TX and NEXT modified outside (min ACKs is 2)
                    #     pass

                    # else:
                    #     if(SEND_CTRL):
                    #         # Discard, someone is trying to win our channel
                    #         pass
                    #     else:
                    if(not (self.is_ACK() or SEND_CTRL)):
                        # We are in RX mode waiting for someone's control
                        TX = self.header >> 5
                        NEXT = (self.header >> 3) ^ (TX << 2)
                        self.payload = ""
                        self.payloadLength = 0
                        if(TX == TEAM_A):
                            # Team A --> ACK order: B, C, D --> header[6]
                            TX_ACK[0] = (self.header&2)/2
                            print("Team A control received")

                        elif(TX == TEAM_B):
                            # Team B --> ACK order: A, C, D --> header[6]
                            TX_ACK[1] = (self.header&2)/2
                            print("Team B control received")

                        elif(TX == TEAM_C):
                            # Team C --> ACK order: A, B, D --> Never here because previously checked (is not ACK)
                            pass

                        elif(TX == TEAM_D):
                            # Team D --> ACK order: A, B, C --> header[7]
                            TX_ACK[2] = self.header&1
                            print("Team D control received")

                        else:
                            # Never here
                            pass

                        if(TX_ACK[TX]):
                            if(TX_POS[TX]==POS_MAX):
                                TX_CMPLT += 1
                            else:
                                TX_POS[TX] += 1

                    elif(self.isACK()):
                        print("ACK to control received")

            else:
                # Data packet
                self.typ = 1
                if(len(self.frameData) < 2):
                    # Empty data
                    self.payload = ""
                    self.payloadLength = 0
                    return -3

                else:
                    self.payload = ''.join(self.frameData[1:])
                    self.payloadLength = len(self.payload)

            return 0


    # Send given packet (frame payload)
    # Input:
    #       - Packet (self): payload field in frame to be sent (total size <= 32B)
    # Output: OK (0) or ErrNum (-1)
    def send_pkt(self):
        if self.payloadLength > PLOAD_SIZE-HDR_SIZE:
            return -1

        else:
            radio_Tx.write(self.frameData)      # Extra checks can be added (other errors may be possible)
            return 0


    # Check if packet is ACK
    # Input:
    #       - Packet (self): payload field in a frame (total size <= 32B)
    # Output: True or False.
    def is_ACK(self):
        return(packet.typ == 0 and (packet.header>>5)==TX)


    # Check if packet is control
    # Input:
    #       - Packet (self): payload field in a frame (total size <= 32B)
    # Output: True or False.
    def is_control(self):
        return(packet.typ == 0)


    # Check if packet is data
    # Input:
    #       - Packet (self): payload field in a frame (total size <= 32B)
    # Output: True or False.
    def is_data(self):
        return(packet.typ == 1)


    # Check if packet is MY data
    # Input:
    #       - Packet (self): payload field in a frame (total size <= 32B)
    # Output: True or False.
    def is_my_data(self):
            return(packet.is_data() and (packet.header>>5)==MY_TEAM)


    # Check if data and expected position
    # Input:
    #       - Packet (self): payload field in a frame (total size <= 32B)
    # Output: True or False.
    def is_expected_data(self):
        return(packet.is_data() and (packet.header&31)==RX_POS[TX]+1)


    # Check who is next in control packet
    # Input:
    #   - Packet (self): payload field in a frame (total size <= 32B)
    # Output: TX value.
    def tx_ctrl(self):
        return self.header >> 5


    # Generate char list to insert in frame using self header and payload
    # Input:
    #   - Packet (self): payload field in a frame (total size <= 32B)
    # Output: OK (0) or ErrNum
    def generate_frame_data(self):
        self.frameData = list(chr(self.header)+self.payload)
        return 0

# Receive ACKs to Control frames (NOT DATA ACK)
# Input:  None
# Output: True when min ACKs received (1) or False if not (0).
def received_acks():
    acks = 0
    start_time = time.time()
    while(acks < 3 or time.time()<start_time+TACK):
        if(radio_Rx.available([0])):       
            packet = PKT()
            if(packet.read_pkt() == 0):
                if(packet.is_ACK()):
                    # ACK to current Tx
                    #print("ACK to control received")
                    acks += 1

                # else:
                #     # Discarded. Do nothing.
                #     pass

    if(acks < 2):
        # Channel not won
        return False

    else:
        # Recognised as winner. Data can be sent.
        return True


# Receive an ACK to Control frames
# Input:  None
# Output: True when control received or False if not.
def received_ctrl():
    TCTRL = random.uniform(1,2)
    ctrl_rx = False

    packet = PKT()
    start_time = time.time()
    print("Control timer started: %0.3f s"%(TCTRL))
    # While if still not TCTRL but something (wrong) received
    while(time.time()<start_time+TCTRL and not ctrl_rx):
        if(radio_Rx.available(0)):
            # Something received
            print("Something received")
            if(packet.read_pkt() == 0):
                if(packet.is_CTRL()):                    
                    # ACK info updated in read_pkt
                    ctrl_rx = True

    return ctrl_rx, packet


# Wait and read data frames
# Input:  None
# Output: True when MY data is received (1) or False if not (0).
def received_data():
    acks = 0
    start_time = time.time()
    while(time.time()<start_time+TDATA):
        # while(not radio_Rx.available(0) or time.time()<start_time+TACK):
        #     pass
            # time.sleep(0.1)
        
        if(radio_Rx.available(0)):
            packet = PKT()
            if(packet.read_pkt() == 0):
                if(packet.is_my_data()):
                    # Data received
                    data_ok = True
                    if (packet.is_expected_data()):
                        # Position + 1 for TX
                        RX_POS[TX] += 1
                        store_data(TX, packet.payload)
                        if(RX_POS[TX] == POS_MAX):
                                RX_CMPLT += 1

                # else:
                #     # Discarded. Do nothing.
                #     pass

    return data_ok


# Check if MY_TEAM is next to transmit
# Input: None
# Output : True or False.
def i_am_next():
    return NEXT == MY_TEAM


# Data is extracted from text file to be sent. Index provides the position to start (fixed size packets). ### 
# Input:
#       - Text file: object associated to reading file
#       - Index: position to be read, i.e. packet number (int)
# Output: Payload data string
def generate_data(text_file, index = 0):
    file_data = text_file.read()
    #text_in_bin =' '.join('{0:08b}'.format(ord(x), 'b') for x in y)             # Convert the text into binary, in 8-bit format 
    # len_text = len(text_in_bin)

    #payload = PLOAD_SIZE - 1
    #len_packet = payload * 8                                                    # Convert size to bits
    # num_packets_to_send = len_text/len_packet

    # data = text_in_bin[index * len_packet : index * len_packet + len_packet - 1] # a partition of length len_packet of the text_file is taken
    size = PLOAD_SIZE-HDR_SIZE
    if(index < POS_MAX):
        return file_data[index*size:(index+1)*size]
    else:
        return file_data[index*size:]


# Data added to the end of a given file.
# Input:
#       - Text file: object associated to writing file
#       - Data: string to be added at the end of the file
# Output: OK or ErrNum
def append_data(text_file, data):
    if(len(data) < 1):          # Empty string
        return -1

    for j in data: text_file.write(j)   # Write in file

    return 0


# Send ACK to received CTRL (same packet as received but changing ACK field)
# Input:
#       - Packet: payload field in a frame of received CTRL (total size <= 32B)
# Output: OK (0) or ErrNum
def send_ack(packet):
    # tx = packet.tx_ctrl()
    # if(tx == TEAM_A or tx == TEAM_B):
    #     # ACK in 2nd position
    #     packet.header = ((packet.header|2)&251)&254

    # else:
    #     # ACK in 3rd packet
    #     packet.header = ((packet.header|1)&251)&253

    packet.generate_frame_data()
    packet.send_data()

    return 0


# Send data to N(=3) receivers
# Input: None
# Output: OK (0) or ErrNum
def send_data():
    # Sending to team A
    packet = PKT()
    if TX_POS[0] < POS_MAX:
        f = open("text_file_A.txt","r")
        payload = generate_data(f, TX_POS[0])
        packet.generate_pkt(1, payload, 0)
        packet.send_pkt()
        f.close()

    # Sending to team B
    if TX_POS[1] < POS_MAX:
        f = open("text_file_B.txt","r")
        payload = generate_data(f, TX_POS[1])
        packet.generate_pkt(1, payload, 1)
        packet.send_pkt()
        f.close()

    # Sending to team D
    if TX_POS[3] < POS_MAX:
        f = open("text_file_D.txt","r")
        payload = generate_data(f, TX_POS[3])
        packet.generate_pkt(1, payload, 3)
        packet.send_pkt()
        f.close()

    return 0

# Store data to N(=3) receivers
# Input:
#       - TX: transmitter ID
#       - Payload: data to add to file (str)
# Output: OK (0) or ErrNum
def store_data(tx, payload):
    # File from team A
    if tx == TEAM_A:
        file_str = "rx_text_file_A.txt"

    # File from team B
    elif tx == TEAM_B:
        file_str = "rx_text_file_B.txt"

    # File from team D
    elif tx == TEAM_D:
        file_str = "rx_text_file_D.txt"

    else:
        return -1

    if os.path.isfile(file_str):
        f = open(file_str, "a")
    else:
        f = open(file_str, "w")

    append_data(f, payload)
    f.close()

    return 0