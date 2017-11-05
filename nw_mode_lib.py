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
TX = NEXT = "00"                            # Current and next TX
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
TEAM_A = "00"
TEAM_B = "01"
TEAM_C = "10"
TEAM_D = "11"
MY_TEAM = TEAM_C
TX_POS = zeros(3)
RX_POS = zeros(3)
ACK = zeros(3)



#### Function definitions ####

# COMMS initialization
# Input: none
# Output: OK (0) er ErrNum (-1)
def init_comms():

    GPIO.setmode(GPIO.BCM)
    GPIO.setup(GPIO_RX, GPIO.OUT)
    GPIO.output(GPIO_RX,1)
    GPIO.setup(GPIO_TX, GPIO.OUT)
    GPIO.output(GPIO_TX,1)

    # Enable transceivers with CE connected to GPIO_TX (22) and GPIO_RX (24)
    radio_Tx = NRF24(GPIO, spidev.SpiDev())
    radio_Rx = NRF24(GPIO, spidev.SpiDev())
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
    radio_Tx.enableDynamicPayloads()
    radio_Rx.enableDynamicPayloads()

    # Open the writing and reading pipe
    radio_Tx.openWritingPipe(PIPE_TX)
    radio_Rx.openReadingPipe(1, PIPE_RX)

    return 0


# Start network mode. Set a value to initial random timer.
# Input: none
# Output: OK (0) er ErrNum (-1)
def start_network():

    random.seed(None, 2)
    TINIT = random.uniform(5,10)
    return 0


# Given a payload dataset, the packet is arranged to be conformed to standard definitions.
# Input:
#       - Type: Control (0) or Data (1)
#       - RX_ID: Only for data packets, receiver ID
#       - Payload: Bytes corresponding to data, ACKs for control or file data
# Output: Packet (of size PLOAD_SIZE), corresponding to transceiver's frame payload field
def generate_pkt(type, rx_id, payload):

    if type:
        # Data packet
        if (NO VALID RX ID):    # HOW TO CHECK IDs!!
            return -1

        else:
            if len(payload) > (PLOAD_SIZE-HDR_SIZE):
                return -1
            else:
                frame_payload = list("1"+str(rx_id)+str(TX_POS(rx_id))+payload)     # Review how to concatenate strings and bits!!
                return frame_payload

    else:
        # Control packet
        # Payload = ACK1+ACK2+ACK3; NEXT previously updated
        header = "0"+MY_TEAM+NEXT+"000"
        frame_payload = list(header+str(ones[8]*ACK(0))+str(ones[8]*ACK(1))+str(ones[8]*ACK(2)))
        return frame_payload+frame_payload                                                          # Payload repeated twice (8B < 32B)


# Send given packet (frame payload)
# Input:
#       - Packet: payload field in frame to be sent
# Output: OK (0) er ErrNum (-1)
def send_pkt(packet):

    if len(packet) > 32:
        return -1

    else:
        radio_Tx.write(packet)      # Extra checks can be added (other errors may be possible)
        return 0