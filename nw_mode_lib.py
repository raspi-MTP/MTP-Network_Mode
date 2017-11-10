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
WAITING_DATA = 0                            # Flag to know is data frame is expected or control, otherwise
TEAM_A = 0
TEAM_B = 1
TEAM_C = 2
TEAM_D = 3
MY_TEAM = TEAM_C
TX = MY_TEAM                                # TX for current time slot
NEXT = TEAM_D                               # TX for next time slot
TX_POS = zeros(3)
RX_POS = zeros(3)
TX_ACK = zeros(3)
RX_ACK = zeros(3)


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
def start_network():
    random.seed(None, 2)
    TINIT = random.uniform(5,10)

    # Disable CRC for Control packets
    # radio_Tx.disableCRC()
    # radio_Rx.disableCRC()

    # Start timer
    start_time = time.time()
    while(not radio_Rx.available(0) or time.time()<start_time+TINIT):
        sleep(0.2)

    packet = PKT()
    if radio_Rx.available(0):
        # Packet received, check it
        packet.read_pkt()
        #########

    else:
        # Timeout, send control
        packet.generate_pkt(0)
        packet.send_pkt()

    return 0



# Packet class type. It includes:
#       - Type: control (0) or data (1)
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
                    self.header = 128+(rx_id<<5)+TX_POS(rx_id)
                    self.payload = payload
                    self.payloadLength = len(payload)
                    self.frameData = list(chr(self.header)+self.payload)   
                    return 0

        else:
            # Control packet
            # Header = 0 + MY_TEAM_ID + NEXT_ID + 000 (Reserved flags); NEXT previously updated.
            # Payload = ACK0+ACK1+ACK2 (1B each)
            self.typ = typ
            self.header = 0+(MY_TEAM<<5)+(NEXT<<3)+(RX_ACK[0]<<2)+(RX_ACK[1]<<1)+RX_ACK[0]
            self.payload = ""
            self.payloadLength = 0
            self.frameData = list(chr(self.header))  
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
                    TX = self.header >> 5
                    NEXT = (self.header >> 3) ^ (TX << 2)
                    self.payload = ""
                    self.payloadLength = 0
                    if(TX == 0):
                        # Team A --> ACK order: B, C, D --> header[6]
                        TX_ACK[0] = (self.header&2)/2

                    elif(TX==1):
                        # Team B --> ACK order: A, C, D --> header[6]
                        TX_ACK[1] = (self.header&2)/2

                    elif(TX==2):
                        # Team C --> ACK order: A, B, D --> It's us! (CTRL ACK)

                    elif(TX==3):
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
                    return -2

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



# Receive an ACK to Control frames (NOT DATA ACK)
# Input:  None
# Output: OK (0) if minimum ACKs received or ErrNum if not (-1).
def receive_acks():
    acks = 0
    start_time = time.time()
    while(acks < 3 or time.time()<start_time+TACK)
        while(not radio_Rx.available(0) or time.time()<start_time+TACK):
            # sleep(0.1)
        
        if(radio_Rx.available(0)):
            packet = PKT()
            packet.read_pkt()
            if(packet.typ == 0 and (packet.header>>5)==TX):
                # ACK to current Tx
                acks += 1

            else:
                # Discarded. Do nothing.

    if(acks < 2):
        # Channel not won
        return -1

    else:
        # Recognised as winner. Data can be sent.
        return 0



# Receive an ACK to Control frames
# Input:  None
# Output: OK (0) if correct control frame received or ErrNum if not (-1).
def receive_ctrl():
    