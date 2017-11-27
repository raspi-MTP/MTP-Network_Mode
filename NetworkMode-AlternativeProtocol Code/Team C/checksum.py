import crc16

def build_networkctrlpackage(team, seq_number, packages):
    seq_number = bin(seq_number).lstrip('0b')
    while len(seq_number) < 6:
        seq_number = '0' + seq_number
    ctrl = chr(int(team + seq_number, 2)) + chr(packages)

    return (ctrl)

def build_crcpackage(crc):
    crc = bin(crc).lstrip('0b')
    while len(crc) < 16:
        crc = '0' + crc

    byte1 = ''
    byte2 = ''
    i = 0
    while i < 8:
        byte1 = byte1 + crc[i]
        i += 1

    while i < 16:
        byte2 = byte2 + crc[i]
        i += 1

    crc = chr(int(byte1, 2)) + chr(int(byte2, 2))

    return crc

def checkcrc(message, crc):
    if crc16.crc16xmodem(message) == crc:
        return True
    else:
        return False