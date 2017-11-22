from nw_mode_lib import PKT


def main():
    packet = PKT()
    packet.generate_pkt(0)

    packet.send_pkt()



if __name__=='__main__':

    main()