from decouple import config
from Crypto.PublicKey import RSA
import ipfshttpclient
import sqlite3
import io
import rsa
import random
from datetime import datetime
import json
import os


class Certifier():
    def certify(actors, roles):
        for actor in actors:
            Certifier.__read_public_key__(actor)
        Certifier.__skm_public_key__()
        Certifier.__attribute_certification__(roles)

    def read_public_key(actors):
        for actor in actors:
            Certifier.__read_public_key__(actor)

    def skm_public_key():
        Certifier.__skm_public_key__()

    def attribute_certification(roles):
        Certifier.__attribute_certification__(roles)


    def __read_public_key__(actor_name):
        api = ipfshttpclient.connect('/ip4/127.0.0.1/tcp/5001')

        print("Reading keys of " + actor_name)
        reader_address = config('ADDRESS_' + actor_name)
        private_key = config('PRIVATEKEY_' + actor_name)
        app_id_pk_readers = config('APPLICATION_ID_PK_READERS')

        # Connection to SQLite3 reader database
        conn = sqlite3.connect('files/reader/reader.db')
        x = conn.cursor()

        # # Connection to SQLite3 data_owner database
        connection = sqlite3.connect('files/data_owner/data_owner.db')
        y = connection.cursor()

        keyPair = RSA.generate(bits=1024)
        # print(f"Public key:  (n={hex(keyPair.n)}, e={hex(keyPair.e)})")
        # print(f"Private key: (n={hex(keyPair.n)}, d={hex(keyPair.d)})")

        f = io.StringIO()
        f.write('reader_address: ' + reader_address + '###')
        f.write(str(keyPair.n) + '###' + str(keyPair.e))
        f.seek(0)

        hash_file = api.add_json(f.read())
        print(f'ipfs hash: {hash_file}')

        x.execute("INSERT OR IGNORE INTO rsa_private_key VALUES (?,?,?)", (reader_address, str(keyPair.n), str(keyPair.d)))
        conn.commit()

        x.execute("INSERT OR IGNORE INTO rsa_public_key VALUES (?,?,?,?)",
                (reader_address, hash_file, str(keyPair.n), str(keyPair.e)))
        conn.commit()

        y.execute("INSERT OR IGNORE INTO rsa_private_key VALUES (?,?,?)", (reader_address, str(keyPair.n), str(keyPair.d)))
        connection.commit()

        y.execute("INSERT OR IGNORE INTO rsa_public_key VALUES (?,?,?,?)",
                (reader_address, hash_file, str(keyPair.n), str(keyPair.e)))
        connection.commit()

        print('private key: ' + private_key)
        print(os.system('python3.10 blockchain/PublicKeysReadersContract/PKReadersContractMain.py -creator %s -app %s -ipfs %s' % (
            private_key, app_id_pk_readers, hash_file)))

    def __skm_public_key__():
        api = ipfshttpclient.connect('/ip4/127.0.0.1/tcp/5001')

        print("Reading keys of SKM")

        skm_address = config('SKM_ADDRESS')
        skm_private_key = config('SKM_PRIVATEKEY')

        app_id_pk_skm = config('APPLICATION_ID_PK_SKM')

        # Connection to SQLite3 reader database
        conn = sqlite3.connect('files/skm/skm.db')
        x = conn.cursor()

        (publicKey, privateKey) = rsa.newkeys(1024)
        publicKey_store = publicKey.save_pkcs1().decode('utf-8')
        privateKey_store = privateKey.save_pkcs1().decode('utf-8')

        f = io.StringIO()
        f.write('skm_address: ' + skm_address + '###')
        f.write(publicKey_store)
        f.seek(0)

        hash_file = api.add_json(f.read())
        print(f'ipfs hash: {hash_file}')

        x.execute("INSERT OR IGNORE INTO rsa_private_key VALUES (?,?)", (skm_address, privateKey_store))
        conn.commit()

        x.execute("INSERT OR IGNORE INTO rsa_public_key VALUES (?,?,?)", (skm_address, hash_file, publicKey_store))
        conn.commit()

        print(os.system('python3.10 blockchain/PublicKeySKM/PKSKMContractMain.py -creator %s -app %s -ipfs %s' % (
            skm_private_key, app_id_pk_skm, hash_file)))



    def __attribute_certification__(roles):

        app_id_certifier = config('APPLICATION_ID_CERTIFIER')

        api = ipfshttpclient.connect('/ip4/127.0.0.1/tcp/5001') # Connect to local IPFS node (creo un nodo locale di ipfs)

        app_id_certifier = config('APPLICATION_ID_CERTIFIER')
        certifier_private_key = config('CERTIFIER_PRIVATEKEY')

        manufacturer_address = config('ADDRESS_MANUFACTURER')
        supplier1_address = config('ADDRESS_SUPPLIER1')
        supplier2_address = config('ADDRESS_SUPPLIER2')

        # Connection to SQLite3 attribute_certifier database
        conn = sqlite3.connect('files/attribute_certifier/attribute_certifier.db') # Connect to the database
        x = conn.cursor()

        now = datetime.now()
        now = int(now.strftime("%Y%m%d%H%M%S%f"))
        random.seed(now)
        process_instance_id = random.randint(1, 2 ** 63)
        print(f'process instance id: {process_instance_id}')
        
        dict_users = {}
        for actor, list_roles in roles.items():
            dict_users[config('ADDRESS_' + actor)] = [str(process_instance_id)] + [role for role in list_roles]
        print(dict_users)

        f = io.StringIO()
        dict_users_dumped = json.dumps(dict_users)
        f.write('"process_instance_id": ' + str(process_instance_id) + '####')
        f.write(dict_users_dumped)
        f.seek(0)

        file_to_str = f.read()

        hash_file = api.add_json(file_to_str)
        print(f'ipfs hash: {hash_file}')

        x.execute("INSERT OR IGNORE INTO user_attributes VALUES (?,?,?)",
                (str(process_instance_id), hash_file, file_to_str))
        conn.commit()
        print(
            os.system('python3.10 blockchain/AttributeCertifierContract/AttributeCertifierContractMain.py -sender %s -app %s -process %s -hash %s' %
                    (certifier_private_key, app_id_certifier, process_instance_id, hash_file)))
    
    def change_process_id(process_instance_id):
        print(f'process instance id: {process_instance_id}')
        
        with open('../.env', 'r', encoding='utf-8') as file:
            data = file.readlines()
        data[0] = 'PROCESS_INSTANCE_ID=' + str(process_instance_id) + '\n'

        with open('../.env', 'w', encoding='utf-8') as file:
            file.writelines(data)