#!/usr/bin/python

# Network mode library with all required functions
# to run NRF24L01 transceiver over Raspberry Pi and
# communicate with others using TDM-type approach.

# Brian Lavery's lib_nrf24.py library is used for
# Raspberry Pi and "Virtual GPIO" configuration

# MTP Team C. Fall 2017-18. ETSETB, Universitat Politècnica de Catalunya (UPC).




#### Required libraries ####
import sys
import time
import random
from lib_nrf24 import NRF24
import RPi.GPIO as GPIO
import spidev
from math import *



#### Network parameters ####
RF_CH = [0x50, 0x64]                        # UL & DL channels
TX_CMPLT = RX_CMPLT = 0                     # Completed files
PWR_LVL = NRF24.PA_HIGH                     # Transceiver output (HIGH = -6 dBm + 20 dB)
BRATE = NRF24.BR_250KBPS                    # 250 kbps bit rate
TDATA = TACK =  0.1                         # Data and ACK frames timeout (in seconds)
TCTRL = TINIT = 0                           # Control frame and initialization random timeouts (in seconds)
PLOAD_SIZE = 32                             # Payload size corresponding to data in one frame (32 B max)
HDR_SIZE = 1                                # Header size inside payload frame
PIPE_TX = [0xc2, 0xc2, 0xc2, 0xc2, 0xc2]    # TX pipe address
PIPE_RX = [0xe7, 0xe7, 0xe7, 0xe7, 0xe7]    # RX pipe address
GPIO_TX = 22                                # TX transceiver's CE to Raspberry GPIO
GPIO_RX = 24                                # RX transceiver's CE to Raspberry GPIO
WAITING_DATA = False                        # Flag to know whether data frame is expected or control, otherwise
SEND_CTRL = False                           # Flag to know if control frame must be sent
TEAM_A = 0
TEAM_B = 1
TEAM_C = 2
TEAM_D = 3
MY_TEAM = TEAM_C
TX = MY_TEAM                                # TX for current time slot
NEXT = TEAM_D                               # TX for next time slot
TX_POS = zeros(4)
RX_POS = zeros(4)
TX_ACK = zeros(4)
RX_ACK = zeros(4)



#### Radio interfaces ####
radio_Tx = NRF24(GPIO, spidev.SpiDev())
radio_Rx = NRF24(GPIO, spidev.SpiDev())



#### Class and function definitions ####

# COMMS initialization
# Input:  None
# Output: OK (0) or ErrNum (-1)
def init_comms():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(GPIO_RX, GPIO.OUT)
    GPIO.output(GPIO_RX,1)
    GPIO.setup(GPIO_TX, GPIO.OUT)
    GPIO.output(GPIO_TX,1)

    # Enable transceivers with CE connected to GPIO_TX (22) and GPIO_RX (24)
    radio_Tx.begin(0, GPIO_TX)
    radio_Rx.begin(1, GPIO_RX)

    # Payload Size set to defined value
    radio_Tx.setPayloadSize(PLOAD_SIZE)
    radio_Rx.setPayloadSize(PLOAD_SIZE)

    # We choose the channels to be used for one and the other transceiver
    radio_Tx.setChannel(channel_TX)
    radio_Rx.setChannel(channel_RX)

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
    radio_Rx.openReadingPipe(1, PIPE_RX)

    return 0


# Start network mode. Set a value to initial random timer. Wait until TINIT or CTRL received.
# Input:  None
# Output: OK (0) or ErrNum (-1)
def start_network():                # main_network
    random.seed(54321)
    TINIT = random.uniform(5,10)

    # Disable CRC for Control packets
    # radio_Tx.disableCRC()
    # radio_Rx.disableCRC()

    # Start timer
    start_time = time.time()

    while(not radio_Rx.available(0) or time.time() < (start_time + TINIT)):
        sleep(0.2)

    if(not radio_Rx.available(0)):
        SEND_CTRL = 1

    while(True):                    # Check files sent/received
        if SEND_CTRL:
            # Send control (maybe TINIT or TCTRL)
            packet = PKT()
            packet.generate_pkt(0)
            packet.send_pkt()

            # Wait for ACKs
            if(receive_acks()):
                # 2 or 3 ACKs received
                # send_data()  -->  x3 packetS

            else:
                # Timeout or less than 2 ACKs
                # Wait control

        else:
            if(WAITING_DATA):
                # Data frame to be received
                packet = PKT()
                if(receive_data()):
                    # Data received
                    # ACK = 1 for TX data
                    RX_ACK[TX] = 1

                else:
                    # Timeout TDATA
                    # ACK = 0 for TX data
                    RX_ACK[TX] = 1

                WAITING_DATA = False
                if(i_am_next()):
                    TX = MY_TEAM
                    NEXT = TEAM_D
                    SEND_CTRL = True

                else:
                    SEND_CTRL = False


                # After TDATA --> WAITING DATA = False

            else:
                # Control frame to be received
                if(receive_ctrl()):
                    # Control received
                    t_send_ack = random.uniform(0,0.02)
                    time.sleep(t_send_ack)
                    # Send ACK
                    #############
                    WAITING_DATA = True

                else:
                    # Timeout
                    SEND_CTRL = True
                    continue


        return 0


# Packet class type. It includes:
#       - Type: control (0) or data (1) (int)
#       - Header: flags and identifiers before payload (chr)
#       - Payload: packet data (string)
#       - Payload Length: int with total length of payload (int in B)
#       - Frame Data: header+payload (chr list)
class PKT:
    def __init__(typ=0,header=chr(0),payload=""):
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
                    # Check if ACK is expected (I am TX) or CTRL (I am RX) !!!!!!!!!!
                    if(self.is_ACK()):
                        # ACK to me
                        TX = MY_TEAM
                        NEXT = TEAM_D

                    else: 
                        TX = self.header >> 5
                        NEXT = (self.header >> 3) ^ (TX << 2)
                        self.payload = ""
                        self.payloadLength = 0
                        if(TX == TEAM_A):
                            # Team A --> ACK order: B, C, D --> header[6]
                            TX_ACK[0] = (self.header&2)/2

                        elif(TX == TEAM_B):
                            # Team B --> ACK order: A, C, D --> header[6]
                            TX_ACK[1] = (self.header&2)/2

                        elif(TX == TEAM_C):
                            # Team C --> ACK order: A, B, D --> It's us! (CTRL ACK)

                        elif(TX == TEAM_D):
                            # Team D --> ACK order: A, B, C --> header[7]
                            TX_ACK[2] = self.header&1

                        else:
                            # Never here

            else:
                # Data packet
                self.typ = 1
                if(len(self.frameData) < 2):
                    # Empty data
                    self.payload = ""
                    self.payloadLength = 0
                    return -3

                else:
                    self.payload = str(self.frameData[1:])
                    self.payloadLength = len(self.payload)


    # Send given packet (frame payload)
    # Input:
    #       - Packet (self): payload field in frame to be sent (total size <= 32B)
    # Output: OK (0) or ErrNum (-1)
    def send_pkt(self):
        if packet.payloadLength > PLOAD_SIZE-HDR_SIZE:
            return -1

        else:
            radio_Tx.write(self.frameData)      # Extra checks can be added (other errors may be possible)
            return 0


    # Check if packet is ACK
    # Input:
    #       - Packet (self): payload field in frame to be sent (total size <= 32B)
    # Output: Yes (1) or No (0)
    def is_ACK(self):
        return(packet.typ == 0 and (packet.header>>5)==TX)


    # Check if packet is control
    # Input:
    #       - Packet (self): payload field in frame to be sent (total size <= 32B)
    # Output: Yes (1) or No (0)
    def is_control(self):
        return(packet.typ == 0)


    # Check if packet is data
    # Input:
    #       - Packet (self): payload field in frame to be sent (total size <= 32B)
    # Output: Yes (1) or No (0)
    def is_data(self):
        return(packet.typ == 1)


    # Check if packet is MY data
    # Input:
    #       - Packet (self): payload field in frame to be sent (total size <= 32B)
    # Output: Yes (1) or No (0)
    def is_my_data(self):
            return(packet.is_data() and (packet.header>>5)==MY_TEAM)


    # Check if data and expected position
    # Input:
    #       - Packet (self): payload field in frame to be sent (total size <= 32B)
    # Output: Yes (1) or No (0)
    def is_expected_data(self):
        return(packet.is_data() and (packet.header&(0b00011111))==RX_POS[TX]+1)


    # sgrbd
    def tx_ctrl(self):
        return self.header >> 5


# Receive an ACK to Control frames (NOT DATA ACK)
# Input:  None
# Output: True when min ACKs received (1) or False if not (0).
def receive_acks():
    acks = 0
    start_time = time.time()
    while(acks < 3 or time.time()<start_time+TACK)
        while(not radio_Rx.available(0) or time.time()<start_time+TACK):
            # sleep(0.1)
        
        if(radio_Rx.available(0)):
            packet = PKT()
            packet.read_pkt()
            if(packet.is_ACK()):
                # ACK to current Tx
                acks += 1

            else:
                # Discarded. Do nothing.

    if(acks < 2):
        # Channel not won
        return 0

    else:
        # Recognised as winner. Data can be sent.
        return 1


# Receive an ACK to Control frames
# Input:  None
# Output: True when control received (1) or False if not (0).
def receive_ctrl():
    TCTRL = random.uniform(1,2)
    ctrl_rx = False

    start_time = time.time()
    # While if still not TCTRL but something (wrong) received
    while(time.time()<start_time+TCTRL and not ctrl_rx):
        while(not radio_Rx.available(0)):
            # sleep(0.2)

        if(radio_Rx.available(0)):
            # Something received
            packet = PKT()
            packet.read_pkt()
            if(packet.is_CTRL()):
                # Control Received
                ctrl_rx = True

    if(ctrl_rx):
        # Received control
        return 1
    else:
        # Timeout
        return 0


# Wait and read data frames
# Input:  None
# Output: True when MY data is received (1) or False if not (0).
def receive_data():
    acks = 0
    start_time = time.time()
    while(not data_ok or time.time()<start_time+TACK):
        while(not radio_Rx.available(0) or time.time()<start_time+TACK):
            # sleep(0.1)
        
        if(radio_Rx.available(0)):
            packet = PKT()
            packet.read_pkt()
            if(packet.is_my_data()):
                # Data received
                data_ok = True
                if (packet.is_expected_data()):
                    # Position + 1 for TX
                    RX_POS[TX] += 1

            else:
                # Discarded. Do nothing.

    if(data_ok):
        return 1

    else:
        return 0


# KASDEWFHEFHWEIJ
def i_am_next():
    # TO DO


### Data is extracted from text file to be sent. Index provides the position to start (fixed size packets). ### 
### Input: text file, index
### Output: data payload
def generate_data(index = 0, text_file, pkt):

    f = open(text_file,"r")
    y = f.read()
    text_in_bin =' '.join('{0:08b}'.format(ord(x), 'b') for x in y) # convert the text into binary, in 8-bit format 
    f.close()
    # len_text = len(text_in_bin)

    payload = PLOAD_SIZE - 1
    len_packet = payload * 8 # convert it to bits
    # num_packets_to_send = len_text/len_packet

    data = text_in_bin[index * len_packet : index * len_packet + len_packet - 1] # a partition of length len_packet of the text_file is taken
    pkt.payload = data # save data in the payload of the packet (NO SÉ SI ES NECESARIO HACERLO AQUÍ)

### Data added to the end of a given file.
### Input: text file, data
### Output: OK or ErrNum
def append_data(text_file, data):

    if(len(data) < 1): # Empty string
        return -1

    f = open(text_file,"a") # open file to append something
    for j in data: f.write(j) # write in file
    f.close()

    return 0