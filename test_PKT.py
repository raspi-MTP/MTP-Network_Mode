from nw_mode_lib import PKT


def main():
    packet = PKT()
    packet.generate_pkt(0)

    print(bin(ord(packet.header)))
    print(packet.frameData)



if __name__=='__main__':

    main()