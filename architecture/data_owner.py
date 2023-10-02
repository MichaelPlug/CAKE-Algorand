import socket
import ssl
from hashlib import sha512
import sqlite3
import json
from decouple import config
import sqlite3
import argparse
from connector import Connector

SOCKET_MAX_LENGTH = 4096

class CAKEDataOwner(Connector):

    def __init__(self, process_instance_id = config('PROCESS_INSTANCE_ID')):
        super().__init__("files/data_owner/data_owner.db", 5051, process_instance_id=process_instance_id)
        self.manufacturer_address = config('ADDRESS_MANUFACTURER')
        return
    
    """
    function to handle the sending and receiving messages.
    """
    def send(self, msg):
        message = msg.encode(self.FORMAT)
        msg_length = len(message)
        send_length = str(msg_length).encode(self.FORMAT)
        send_length += b' ' * (self.HEADER - len(send_length))
        self.conn.send(send_length)
        # print(send_length)
        self.conn.send(message)
        receive = self.conn.recv(60000).decode(self.FORMAT)
        if len(receive) != 0:
            print(receive)
            if receive[:15] == 'Number to sign:':
                print("Process instance id:", self.process_instance_id)
                print("Manufacturer address:", self.manufacturer_address)
                print("Number to sign:", receive[16:])
                self.x.execute("INSERT OR IGNORE INTO handshake_number VALUES (?,?,?)",
                        (self.process_instance_id, self.manufacturer_address, receive[16:]))
                self.connection.commit()
            if receive[:23] == 'Here is the message_id:':
                self.x.execute("INSERT OR IGNORE INTO messages VALUES (?,?,?)", (self.process_instance_id, self.manufacturer_address, receive[16:]))
                self.connection.commit()

    def handshake(self):
        print("Start handshake")
        self.send("Start handshake§" + self.manufacturer_address)
        self.disconnect()
        return
    
    def cipher_data(self, message_to_send, entries_string, policy_string):
        signature_sending = self.sign_number()
        self.send("Cipher this message§" + message_to_send + '§' + entries_string + '§' + policy_string + '§' + self.manufacturer_address   + '§' + str(signature_sending))
        self.disconnect()
        return
    
    def sign_number(self):
        print("Process instance id:", self.process_instance_id)
        self.x.execute("SELECT * FROM handshake_number WHERE process_instance=?", (self.process_instance_id,))
        result = self.x.fetchall()
        print(result)
        number_to_sign = result[0][2]
        return super().sign_number(number_to_sign, self.manufacturer_address)
    
if __name__ == "__main__":
    # f = open('files/data.json')
    process_instance_id = config('PROCESS_INSTANCE_ID')
    print("process_instance_id: " + process_instance_id + "\n\n")

    manufacturer_address = config('ADDRESS_MANUFACTURER')

    FILE_TEST = True
    if FILE_TEST:
        g = open('files/bitcoin.json')
        entries = [['simple.pdf'], ['simple.pdf'], ['simple.pdf']]
        
    else:
        g = open('files/data.json')
        entries = [['ID', 'SortAs', 'GlossTerm'], ['Acronym', 'Abbrev'], ['Specs', 'Dates']]

    entries_string = '###'.join(str(x) for x in entries)

    message_to_send = g.read()

    policy = [process_instance_id + ' and (MANUFACTURER or SUPPLIER)',
            process_instance_id + ' and (MANUFACTURER or (SUPPLIER and ELECTRONICS))',
            process_instance_id + ' and (MANUFACTURER or (SUPPLIER and MECHANICS))']
    policy_string = '###'.join(policy)

    sender = manufacturer_address

    parser = argparse.ArgumentParser()
    parser.add_argument('-hs' ,'--hanshake', action='store_true')
    parser.add_argument('-c','--cipher', action='store_true')
    dataOwner= CAKEDataOwner()
    args = parser.parse_args()
    if args.hanshake:
       #dataOwner.send("Start handshake§" + sender)
        dataOwner.handshake()

    if args.cipher:
        #signature_sending = dataOwner.sign_number()
        dataOwner.cipher_data(message_to_send, entries_string, policy_string)
        #message = "Cipher this message|" + message_to_send + '|' + entries_string + '|' + policy_string + '|' + sender + '|' + str(signature_sending)
        #dataOwner.send("Cipher this message§" + message_to_send + '§' + entries_string + '§' + policy_string + '§' + sender + '§' + str(signature_sending))
    dataOwner.disconnect()
