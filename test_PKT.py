from nw_mode_lib import *


def main():
    init_comms()

    packet = PKT()
    packet.generate_pkt(0)

    start_time = time.time()
    while(True):
        while(not radio_Rx.available(0) and time.time() < start_time + 5):
            packet.send_pkt()
            #print("Nothing received :(")

        if radio_Rx.available(0):
            packet.read_pkt()
            print("Received ACK: "+packet.header)
        else:
            print("TIMEOUT")



    # Wait for ACK
    # while(not radio_Rx.available(0) and time.time() < start_time + 10):
    #     print("Nothing received :(")

    # if radio_Rx.available(0):
    #     print(packet.header)
    # else:
    #     print("TIMEOUT!")



if __name__=='__main__':

    main()