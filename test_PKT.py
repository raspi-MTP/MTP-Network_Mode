from nw_mode_lib import *


def main():
    init_comms()

    packet = PKT()
    packet.generate_pkt(0)

    packet.send_pkt()

    # Wait for ACK
    start_time = time.time()
    while(not radio_Rx.available(0) and time.time() < start_time + 10):
        print("Nothing received :(")

    if radio_Rx.available(0):
        print(packet.header)
    else:
        print("TIMEOUT!")



if __name__=='__main__':

    main()