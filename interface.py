#!/usr/bin/env python
#
# Mission Directory PDF Maker
# (Grabs missionary info from IMOS and dumps it into a pretty PDF)
#
import getpass
import IMOS

if __name__ == '__main__':
    while True:
        username = raw_input("[?] IMOS Username: ")
        password = getpass.getpass("[?] IMOS Password: ")
        print "-" * 70
        session = IMOS.session(username, password)
     
        print "[+] Attempting Login..."
        if not session.login():
            print "[!] Login failed, try again!"
            print "-" * 70
            continue

        print "-" * 70
        print "[+] Starting directory creation..."
        session.dump_missionaries_info()
        print "[+] Directory creation complete!"
        raw_input("[+] Press enter to exit...")
        break