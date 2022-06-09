#!/usr/bin/env python3.8
# -*- encoding: utf-8 -*-
# -*- coding: utf-8 -*-

import imaplib
import email
import base64
import multiprocessing
from os import stat
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
        status, raw_content = self.connection.uid('fetch', mail_id, '(RFC822)')
        if status == 'OK':
            msg = email.message_from_bytes(raw_content[0][1])
            #print(msg.keys())

        return {
            'status' : status,
            'subject' : msg['Subject'],
            'from' : msg['From']
        }

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
        self.on_new_event = self._on_new_foo
        self.on_remove_event = self._on_remove_foo
        self.events_list = []

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
                    current_time = datetime.now()
                    if new_mails:
                        self.on_new_event(event=new_mails, event_time = current_time)
                    if removed_mails:
                        self.on_remove_event(event=removed_mails, event_time = current_time)
                        #print('new : ',\
                        #[(self.get_mail_header(id)['from'], self.get_mail_header(id)['subject']) for id in new_mails])
                    start_index_list = index_list
                self.disconect()
            except KeyboardInterrupt:
                self.disconect()

    def _on_new_foo(self, event : list, event_time : datetime) -> None:
        self.events_list.append((f'new at {event_time}', event))

    def _on_remove_foo(self, event : list, event_time : datetime) -> None:
        self.events_list.append((f'remove at {event_time}', event))

class EmailFilter(multiprocessing.Process):

    process_list =[]

    def __init__(self, mail_id):
        super(EmailFilter, self).__init__()
        self.mail_id = mail_id
        print('process init')
        EmailFilter.process_list.append(self)

    def run(self):
        print('process run')
        mail_box = Email()
        mail_box.connection.select('INBOX')
        mail_header = mail_box.get_mail_header(self.mail_id)
        if mail_header['subject'] == 'move':
            print('matching')
            self.move_email(folder = 'Trash', mail_box=mail_box)
        mail_box.disconect()

    def move_email(self, folder : str, mail_box : Email):
        status, _ = mail_box.connection.uid('COPY', self.mail_id, folder)
        mail_box.connection.uid('STORE', self.mail_id, '-FLAGS', r'(\Seen)')
        if status == 'OK':
            mail_box.connection.uid('STORE', self.mail_id , '+FLAGS', r'(\Deleted)')
            mail_box.connection.expunge()

    def __del__(self):
        print('del ', self)

def filter_starter(event, event_time):
    for mail_id in event:
        email_filter = EmailFilter(mail_id)
        email_filter.start()

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
    #print(lst.connection.list())
    lst.on_new_event = filter_starter
    lst.on_remove_event = lambda event, event_time : print(f'at {event_time} removed {event}')

    lst.run()
    print(lst.events_list)
    for process in EmailFilter.process_list:
        process.join()
