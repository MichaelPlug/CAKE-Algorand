
from hashlib import sha512
from decouple import config
from connector import Connector
import argparse

class CAKEClient(Connector):
    ### Initialize the class with the information to connect to the server and the DB.
    ### The information of message_id, reader_address and slice_id are optional,
    ### they are used to sign the message and the can be changed or setted later
    def __init__(self, process_instance_id = config('PROCESS_INSTANCE_ID'), message_id = "", reader_address = "", slice_id = ""):

        super().__init__(path_to_db='files/reader/reader.db', port=5052, process_instance_id=process_instance_id)
        self.__setArgs__(message_id, reader_address, slice_id)
        return

    def __setArgs__(self, message_id, reader_address, slice_id = ""):
        self.message_id = message_id
        self.reader_address = reader_address
        self.slice_id = slice_id
        return

    def send(self, msg):
        message = msg.encode(self.FORMAT)
        msg_length = len(message)
        send_length = str(msg_length).encode(self.FORMAT)
        send_length += b' ' * (self.HEADER - len(send_length))
        self.conn.send(send_length)
        print(message)
        self.conn.send(message)
        receive = self.conn.recv(6000).decode(self.FORMAT)
        if len(receive) != 0:
            print(receive)
            if receive[:15] == 'number to sign:':
                self.x.execute("INSERT OR IGNORE INTO handshake_number VALUES (?,?,?,?)",
                        (self.process_instance_id, self.message_id, self.reader_address, receive[16:]))
                self.connection.commit()

            if receive[:25] == 'Here is IPFS link and key':
                key = receive.split('\n\n')[0].split("b'")[1].rstrip("'")
                ipfs_link = receive.split('\n\n')[1]
    
                self.x.execute("INSERT OR IGNORE INTO decription_keys VALUES (?,?,?,?,?)",
                        (self.process_instance_id, self.message_id, self.reader_address, ipfs_link, key))
                self.connection.commit()

            if receive[:26] == 'Here is plaintext and salt':
                plaintext = receive.split('\n\n')[0].split('Here is plaintext and salt: ')[1]
                salt = receive.split('\n\n')[1]

                self.x.execute("INSERT OR IGNORE INTO plaintext VALUES (?,?,?,?,?,?)",
                        (self.process_instance_id, self.message_id, self.slice_id, self.reader_address, plaintext, salt))
                self.connection.commit()
                print(plaintext)
        return receive
    
    def handshake(self):
        self.send("Start handshake§" + str(self.message_id) + '§' + self.reader_address)
        self.disconnect()
        return
    
    def generate_key(self):
        signature_sending = self.sign_number()
        self.send("Generate my key§" + self.message_id + '§' + self.reader_address + '§' + str(signature_sending))
        self.disconnect()
        return
    
    def access_data(self):
        signature_sending = self.sign_number()
        self.send("Access my data§" + self.message_id + '§' + self.slice_id + '§' + self.reader_address + '§' + str(signature_sending))
        self.disconnect()
        return
    
    def full_request(self):
        self.handshake()
        self.generate_key()
        self.access_data()
        return
    
    def sign_number(self):
        self.x.execute("SELECT * FROM handshake_number WHERE process_instance=? AND message_id=? AND reader_address=?",
                    (self.process_instance_id, self.message_id, self.reader_address))
        result = self.x.fetchall()
        print(result)
        number_to_sign = result[0][3]
        return super().sign_number(number_to_sign, self.reader_address)    
    
if "__name__" == "__main__":
    message_id = '2194010642773077942'
    slice_id = '10213156370442080575'
    reader_address = '47J2YQQJMLLT3IPG2CH2UY4KWQITXDGQFXVXX5RN7HNBJCTG7VBZP6SGGQ'

    parser = argparse.ArgumentParser(description="Client request details", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-m', '--message_id', type=str, default=message_id, help='Message ID')
    parser.add_argument('-s', '--slice_id', type=str, default=slice_id, help='Slice ID')
    parser.add_argument('-rd', '--reader_address', type=str, default=reader_address, help='Reader address')

    #TODO: add the other arguments
    parser.add_argument('-hs', '--handshake', action='store_true', help='Handshake')
    parser.add_argument('-gs', '--generate_key', action='store_true', help='Generate key')
    parser.add_argument('-ad','--access_data',  action='store_true', help='Access data')
    args = parser.parse_args()

    message_id = args.message_id
    slice_id = args.slice_id
    reader_address = args.reader_address

    print("message_id: ", message_id)
    print("slice_id: ", slice_id)
    print("reader_address: ", reader_address)

    client = CAKEClient(message_id=message_id, reader_address=reader_address, slice_id=slice_id)
    if args.handshake:
        client.handshake()
        #send("Start handshake§" + str(message_id) + '§' + reader_address) #and exit()

    if args.generate_key or args.access_data:
        #signature_sending = sign_number(message_id)
        if args.generate_key:
            client.generate_key()
            #send("Generate my key§" + message_id + '§' + reader_address + '§' + str(signature_sending))
        if args.access_data:
            client.access_data()
            #send("Access my data§" + message_id + '§' + slice_id + '§' + reader_address + '§' + str(signature_sending))
    #send(DISCONNECT_MESSAGE)
