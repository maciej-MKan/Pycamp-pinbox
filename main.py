#!/usr/bin/env python3.8
# -*- encoding: utf-8 -*-
# -*- coding: utf-8 -*-

import imaplib
import email
import base64
from time import sleep
from datetime import datetime

class Email:
    from config import domian, port, user, ssl_connection, password as _password

    def __init__(self) -> None:
        self.connection = self.connect_ssl() if self.ssl_connection else self.connect()

    def connect(self):
        connection = imaplib.IMAP4(host=self.domian, port=self.port)
        print(connection.login(self.user, self._password))
        return connection

    def connect_ssl(self):
        connection = imaplib.IMAP4_SSL(host=self.domian, port=self.port)
        print(connection.login(self.user, self._password))
        return connection

    def disconect(self):
        self.connection.close()
        self.connection.logout()

    def get_mails(self, folder = 'INBOX'):
        try:
            self.connection.select(folder)
            #status, index_list = self.connection.search(None, 'ALL')
            status, uids = self.connection.uid('search', None, 'ALL')
        except (imaplib.IMAP4.abort, imaplib.IMAP4_SSL.abort):
            print('reconect')
            self.disconect()
            self.__init__()
            self.get_mails()
        else:
            return status, uids[0].split()

    def get_mail_header(self, mail_id):
        status, raw_content = self.connection.uid('fetch',mail_id, '(RFC822)')
        if status == 'OK':
            msg = email.message_from_bytes(raw_content[0][1])
            #print(msg.keys())
            print(msg['Message-ID'])
            print(msg['Subject'])
            print(msg['From'])

    def get_mail_content(self, mail_id):
        status, raw_content = self.connection.uid('fetch',mail_id, '(RFC822)')
        if status == 'OK':
            msg = email.message_from_bytes(raw_content[0][1])
            if msg.is_multipart():
                msg_content = ''

                for part in msg.get_payload():
                    if part.get_content_type() == 'text/plain':
                        print(part)
                        msg_content += part.get_payload()
                    # if part.get_content_type() == 'text/html':

                    #     msg_content += part.get_payload()
            else:
                if msg.get_content_type() == 'text/html':
                    msg_content = base64.b64decode(msg.get_payload()).decode('utf-8')

        return msg_content

class EmailListener(Email):

    def __init__(self, freqency : int) -> None:
        super().__init__()
        self.freq = freqency
        self.stop = False

    def run(self):
        status, start_index_list = self.get_mails()
        if status == 'OK':
            try:
                while not self.stop:
                    sleep_time = 60 // self.freq
                    #print(sleep_time)
                    sleep(sleep_time)
                    status , index_list = self.get_mails()
                    if status != 'OK':
                        self.stop = True
                    new_mails = list(set(index_list) - set(start_index_list))
                    removed_mails = list(set(start_index_list) - set(index_list))
                    if new_mails or removed_mails:
                        print(f'new : {new_mails} \nremoved : {removed_mails}')
                        print(datetime.now())
                    start_index_list = index_list
                self.disconect()
            except KeyboardInterrupt:
                self.disconect()

if __name__ == '__main__':
    # inbox = Email()

    # status, index_list = inbox.get_mails()
    # print(index_list)
    # if status == 'OK':
    #     for i in index_list:
    #         print(i)
    #         print(inbox.get_mail_header(i))

    #inbox.disconect()
    lst = EmailListener(freqency=4)

    lst.run()