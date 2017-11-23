from nw_mode_lib import *

try:
    def main():
        init_comms()

        # Active mode
        # packet = PKT()
        # packet.generate_pkt(0)

        # while(True):
        #     start_time = time.time()
        #     while(not radio_Rx.available(0) and time.time() < start_time + 5):
        #         packet.send_pkt()
        #         #print("Nothing received :(")

        #     if radio_Rx.available(0):
        #         packet.read_pkt()
        #         print("Received ACK: "+packet.header)
        #     else:
        #         print("TIMEOUT")


        # Passive mode
        while(True):
            rx_ctrl, packet = received_ctrl()

            if(rx_ctrl):
                # Control received. TX and NEXT updated.
                #print(packet.header)
                t_send_ack = random.uniform(0,0.05)
                time.sleep(t_send_ack)
                # Send ACK
                send_ack(packet)
                WAITING_DATA = True

            else:
                # Timeout
                print("Timeout")
                TX = MY_TEAM
                NEXT = TEAM_D
                SEND_CTRL = True


    if __name__=='__main__':

        main()

except KeyboardInterrupt:
    #radio_Rx.closeReadingPipe(1)
    radio_Rx.end()
    radio_Tx.end()

    # GPIO.output(23,0)
    # GPIO.output(22,0)
    GPIO.cleanup()