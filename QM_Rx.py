try:

    import RPi.GPIO as GPIO
    from lib_nrf24 import NRF24
    import time
    import spidev

    GPIO.setmode(GPIO.BCM)
    GPIO.setup(22, GPIO.OUT)
    GPIO.output(22, 1)
    GPIO.setup(23, GPIO.OUT)
    GPIO.output(23,1)
    
    print("Receiver")
    pipes = [0xe7, 0xe7, 0xe7, 0xe7, 0xe7]
    #pipes = [0xc2, 0xc2, 0xc2, 0xc2, 0xc2]

    radio = NRF24(GPIO, spidev.SpiDev())
    radio.begin(1, 22)
    radio.setPayloadSize(32)
    radio.setChannel(40)
    #radio.setChannel(0x64)

    radio.setDataRate(NRF24.BR_250KBPS)#2MBPS)
    radio.setPALevel(NRF24.PA_MIN)
    radio.setAutoAck(False)
    radio.enableDynamicPayloads()

    radio.openReadingPipe(1, pipes)
    radio.printDetails()
    print("///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////")

    frame = []

    print("Waiting Ping")

    while True:
        radio.startListening()
        while not radio.available(0):
            time.sleep(1/100)
       	radio.read(frame, radio.getDynamicPayloadSize())
        str_frame = ""
        for c in range(0, len(frame)):
        	str_frame += chr(frame[c])
        print("Received Message")
        #print(str_frame)
        #print(radio.testRPD())
            
except KeyboardInterrupt:
    GPIO.output(22,0)
    GPIO.output(23,0)
    #GPIO.output(24,0)
    GPIO.cleanup()
