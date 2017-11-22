from nw_mode_lib


def main():
    init_comms()

    packet = PKT()
    packet.generate_pkt(0)

    packet.send_pkt()

    # Wait for ACK
    start_time = time.time()
    while(not radio_Rx.available(0) and time.time() < start_time + 10):
        print("Nothing received :(")

    print(packet.header)



if __name__=='__main__':

    main()