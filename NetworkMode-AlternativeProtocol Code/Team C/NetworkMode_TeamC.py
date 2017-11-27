import RPi.GPIO as GPIO
from lib_nrf24 import NRF24
import time
import spidev
import bz2
import binascii
import io
import struct
import hashlib
import crc16
import checksum

# ------------------------------------System Startup-----------------------------------------

#---- Transmission channel
this_team_freq = 0x30
chtx = this_team_freq

#--- Inicial Reception channel
chrx = 0x10

GPIO.setmode(GPIO.BCM)
GPIO.setup(20, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Input Button: Start
GPIO.setup(16, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Input Button: Stop ALL (finish the execution of the script)
GPIO.setup(24, GPIO.IN) # External Interruption
GPIO.setup(19, GPIO.OUT)  # Output Led: Transmitting
GPIO.setup(26, GPIO.OUT)  # Output Led: Receiving

GPIO.output(19, False)
GPIO.output(26, False)

pipes = [[0xe7, 0xe7, 0xe7, 0xe7, 0xe7], [0xc2, 0xc2, 0xc2, 0xc2, 0xc2]]

# Setup Transceiver 1: Transmitter
radio = NRF24(GPIO, spidev.SpiDev())
radio.begin(0, 17)
radio.setPayloadSize(32)
radio.setChannel(chtx)
radio.setDataRate(NRF24.BR_250KBPS)
radio.setPALevel(NRF24.PA_MIN)
radio.setAutoAck(False)
radio.enableDynamicPayloads()
radio.enableAckPayload()

# Setup Transceiver 2: Receiver
radio2 = NRF24(GPIO, spidev.SpiDev())
radio2.begin(1, 27)
radio2.setPayloadSize(32)
radio2.setChannel(chrx)
radio2.setDataRate(NRF24.BR_250KBPS)
radio2.setPALevel(NRF24.PA_MIN)
radio2.setAutoAck(False)
radio2.enableDynamicPayloads()
radio2.enableAckPayload()

reception_completed = False
compress_rate = 9


# -------------------File handling variables and functions-----------------------------------------------
teams_letters = ['A', 'B', 'D']
teams_binary = ['00', '01', '11']
team_frequencies = [0x10, 0x20, 0x40]

packages_team_list = [[], [], []]
dir_to_files=["ctoa.txt", "ctob.txt", "ctod.txt"]
compressed_files = ["", "", ""]
packages_per_team = [0, 0, 0]
team_identifications = [bin(0), bin(1), bin(2)]
number_of_teams = 3


def build_packages_to_send():

    # Open team X file
    # compress team X file
    # Build iterative packages for each team adding header ID
    # Repeat for the others
    for team in range(number_of_teams):
        current_file = open(dir_to_files[team], 'rb')
        packages_per_team[team], compressed_files[team] = network_compression(current_file)
        current_file.close()
        compressed = open("comp_testfileS.txt", "r")
        for current_num in range(packages_per_team[team]):
            part_to_compose = compressed.read(28)
            ctrl = checksum.build_networkctrlpackage(teams_binary[team], current_num, packages_per_team[team])
            message = ctrl + part_to_compose
            crc = crc16.crc16xmodem(message)
            crc2 = checksum.build_crcpackage(crc)
            message = crc2 + message
            packages_team_list[team].append(message)
        compressed.close()


number_packages_to_receive = [0, 0, 0]
received_packages_per_team = [[], [], []]
fully_received_packages = [False, False, False]
final_received_file = ["", "", ""]
# This variable should be changed when changing frequency
current_receiving_team = 0
missdestination_total_packages = 0


def arrange_packages_per_team(mss):
    # Extract team ID
    # If the destination of this package is to Us, save, else keep going
    global missdestination_total_packages

    crc = mss[0] + mss[1]
    ctrl = mss[2] + mss[3]
    team_id, seq_number, number_packages_to_receive[current_receiving_team], crc = translate_networkctrlpackage(ctrl, crc)
    # print number_packages_to_receive[current_receiving_team], seq_number, team_id, seq_number

    if team_id  == '10' and checksum.checkcrc(mss[2:], crc) and not fully_received_packages[current_receiving_team]:
        # Extract total packages and THIS package position
        # Check if the list is empty/not initialized, then initialize it
        if not received_packages_per_team[current_receiving_team]:
            received_packages_per_team[current_receiving_team] = [""]*number_packages_to_receive[current_receiving_team]

        received_packages_per_team[current_receiving_team][seq_number] = mss[4:]
        print('Data Stored - team: ' + teams_letters[current_receiving_team] + ' Package: ' + str(seq_number))

        if received_packages_per_team[current_receiving_team].count("") == 0:
            print('Package from team ' + teams_letters[current_receiving_team] + ' fully received, begin the reconstruction')
            for pack in received_packages_per_team[current_receiving_team]:
                final_received_file[current_receiving_team] = final_received_file[current_receiving_team] + pack

            fully_received_packages[current_receiving_team] = True
            comp_file = open('Received_compressed' + teams_letters[current_receiving_team] + '.txt', "w")
            comp_file.write(final_received_file[current_receiving_team])
            comp_file.close()

    else:
        #print("Package destinated to other group")
        missdestination_total_packages += 1


def network_compression(file):

    print('compressing file 1')

    long = file.read()
    compressedFile = bz2.compress(long, compress_rate)

    object_compress = open("comp_testfileS.txt", "w")
    object_compress.write(compressedFile)
    file.close()  # Close txt file
    object_compress.close()
    object_compress = open("comp_testfileS.txt", "r")
    compressed_long = object_compress.read()
    object_compress.close()

    size = len(long)
    compress_size = len(compressed_long)
    print("The File's size is: ", size, "Bytes\n", "The compressed file size is", compress_size, "B\n")

    print("Compresion rate= ", compress_size / size)

    # ---- Computing number of packages
    packages = int(len(compressed_long) / 28)
    packages += 1
    print("Number of Packages to send:", packages)

    return packages, "comp_testfileS.txt"


def decompress_files():


    for team in range(number_of_teams):
        
        decompressor = bz2.BZ2Decompressor()
        mensaje = ''
        with open('Received_compressed' + teams_letters[team] + '.txt', 'rb') as input:
            while True:
                block = input.read(64)
                if not block:
                    break
                decompressed = decompressor.decompress(block)
                mensaje += decompressed

        input.close()

        final_file = open("Received_From_Team"+ teams_letters[team] + ".txt", "w")
        final_file.write(mensaje)
        final_file.close()

    print("Decompression Finished")


def translate_networkctrlpackage(ctrl, crc):
    ctrl_B1 = bin(ord(ctrl[0])).lstrip('0b')
    while len(ctrl_B1) < 8:
        ctrl_B1 = '0' + ctrl_B1
    team = ctrl_B1[0] + ctrl_B1[1]
    ctrl_B1 = ctrl_B1[2:]

    seq_number = int(ctrl_B1, 2)
    packages = ord(ctrl[1])

    crc_B1 = bin(ord(crc[0])).lstrip('0b')
    while len(crc_B1) < 8:
        crc_B1 = '0' + crc_B1
    crc_B2 = bin(ord(crc[1])).lstrip('0b')
    while len(crc_B2) < 8:
        crc_B2 = '0' + crc_B2

    crc = int(crc_B1 + crc_B2, 2)

    return team, seq_number, packages, crc


package_index = 0
group_index = 0


def get_next_package_to_send():
    global group_index
    global package_index

    if package_index >= packages_per_team[group_index]:
        package_index = 0
        group_index += 1
    if group_index >= number_of_teams:
        group_index = 0
    # print group_index,package_index
    this_package = packages_team_list[group_index][package_index]
    package_index += 1

    return this_package


reception_completed = False


def get_next_freq_to_receive():
    global current_receiving_team
    global fully_received_packages
    global reception_completed

    if fully_received_packages.count(False) == 0:
        reception_completed = True
        return 0
    else:
        current_receiving_team = current_receiving_team + 1

        if current_receiving_team == number_of_teams:
            current_receiving_team = 0

        if fully_received_packages[current_receiving_team]:
            get_next_freq_to_receive()

def reception_script(channel):

    if not reception_completed:
        mss = ''
        while not radio2.available(0):
                time.sleep(1 / 400)
                if GPIO.input(13) == 0:
                        flag = 1
                        break
        #print('Message available')
        receivedMessage = []
        radio2.read(receivedMessage, radio2.getDynamicPayloadSize())
        for n in receivedMessage:

            if n >= 00 and n <= 255:
                mss += chr(n)
        arrange_packages_per_team(mss)


GPIO.add_event_detect(24, GPIO.FALLING, callback = reception_script, bouncetime = 3)

try:
    
    init_time = int(time.time())
    print('Generating packages to send')
    build_packages_to_send()

    print('Transmission script started')
    GPIO.output(19, True)
    time.sleep(0.5)
    GPIO.output(19, False)

    print('Initializing receiver radio')
    radio2.startListening()
    time.sleep(0.1)
    GPIO.output(26, True)
    it_number = 0
    led = False
    iteration_time = 0
    while GPIO.input(16) != 0:
        global current_receiving_team
        global it_number
        global iteration_time
        global fully_received_packages

        message = get_next_package_to_send()
        radio.write(message)
        time.sleep(0.01)
        led = not led
        GPIO.output(19, led)
                    
        #if not reception_completed and radio2.available(0):
            

        if it_number == 200:

            get_next_freq_to_receive()
            chrx = team_frequencies[current_receiving_team]

            radio2.stopListening()
            time.sleep(0.1)
            radio2.setChannel(chrx)
            radio2.startListening()
            time.sleep(0.1)
            print('Cambio de frequencia realizado, frecuencia actual: ' + str(hex(chrx)))
            t = 0
            it_number = 0
            time.sleep(0.01)
            iteration_time = int(time.time()) - init_time

        if iteration_time >= 100:
            break
        it_number += 1


    for team in range(number_of_teams):

        if not fully_received_packages[team]:

            for pack in received_packages_per_team[team]:
                if pack != "":
                    final_received_file[team] = final_received_file[team] + pack
              
            
            comp_file = open('Received_compressed' + teams_letters[team] + '.txt', "w")
            comp_file.write(final_received_file[team])
            comp_file.close()


    decompress_files()
    GPIO.cleanup()


except:

    GPIO.cleanup()
    radio2.stopListening()
    time.sleep(0.5)
