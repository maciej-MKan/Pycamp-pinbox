#!/usr/bin/env python3.8
# -*- encoding: utf-8 -*-
# -*- coding: utf-8 -*-

import imaplib
import email
import base64
import yaml
import multiprocessing
from time import sleep
from datetime import datetime

class Email:

    def __init__(self, uid : bytes):
        self.mail_id = uid

    @property
    def header(self):
        return self.get_mail_header()

    def get_mail_header(self):
        with EmailBox() as email_box:
            email_box.select_folder('Inbox')
            status, raw_content = email_box.connection.uid('fetch', self.mail_id, '(RFC822)')
            if status == 'OK':
                msg = email.message_from_bytes(raw_content[0][1])
                #print(msg.keys())

        return {
            'status' : status,
            'subject' : msg['Subject'] or "No title",
            'from' : msg['From']
        }

    def get_mail_content(self):
        with EmailBox() as email_box:
            email_box.select_folder('Inbox')
            status, raw_content = email_box.connection.uid('fetch', self.mail_id, '(RFC822)')
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

    def mark_as_unseen(self):
        with EmailBox() as email_box:
            email_box.select_folder('Inbox')
            status = email_box.connection.uid('STORE', self.mail_id, '-FLAGS', r'(\Seen)')
            print(f'store {status}')
            status = email_box.connection.expunge()
            print(f'expunge {status}')

    def move_email(self, folder : str) -> None:
        with EmailBox() as email_box:
            email_box.select_folder('Inbox')
            status, _ = email_box.connection.uid('COPY', self.mail_id, folder)
            print(f'coppy {status}')
            if status == 'OK':
                self.delete_email()

    def delete_email(self, *_):
        with EmailBox() as email_box:
            email_box.select_folder('Inbox')
            status = email_box.connection.uid('STORE', self.mail_id , '+FLAGS', r'(\Deleted)')
            print(f'store {status}')
            status = email_box.connection.expunge()
            print(f'expunge {status}')


    def __repr__(self):
        return str(self.mail_id.decode('utf-8'))

class EmailBox:
    from config import domian, port, user, ssl_connection, password as _password

    def __init__(self) -> None:
        self.connection = None

    def __enter__(self):
        self.get_connection()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconect()

    def get_connection(self):
        try:
            self.connection = self._connect_ssl() if self.ssl_connection else self._connect()
        except ConnectionError as err:
            raise err

    def _connect(self):
        connection = imaplib.IMAP4(host=self.domian, port=self.port)
        status = connection.login(self.user, self._password)
        print(status)
        if status[0] != 'OK':
            raise ConnectionError(status[1])
        return connection

    def _connect_ssl(self):
        connection = imaplib.IMAP4_SSL(host=self.domian, port=self.port)
        status = connection.login(self.user, self._password)
        print(status)
        if status[0] != 'OK':
            raise ConnectionError(status[1])
        return connection

    def disconect(self):
        status, _ = self.connection.close()
        print(f'close {status}')
        status, _ = self.connection.logout()
        print(f'logout {status}')

    def select_folder(self, folder):
        print(self.connection.select(folder))

    def get_mails(self, folder):
        try:
            self.select_folder(folder=folder)
            #status, index_list = self.connection.search(None, 'ALL')
            status, uids = self.connection.uid('search', None, 'ALL')
        except (imaplib.IMAP4.abort, imaplib.IMAP4_SSL.abort) as exc:
            self.get_connection()
            self.get_mails()
        else:
            emails = [Email(uid) for uid in uids[0].split()]
            return status, emails


class EmailListener:

    def __init__(self, freqency : int) -> None:
        self.freq = freqency
        self.stop = False
        self.on_new_event = self._on_new_foo
        self.on_remove_event = self._on_remove_foo
        self.events_list = []

    def run(self):
        status = None
        with EmailBox() as email_box:
            status, emails = email_box.get_mails('Inbox')
            if status == 'OK':
                start_index_list = [mail.mail_id for mail in emails]

        if status == 'OK':
            try:
                while not self.stop:
                    sleep_time = 60 // self.freq
                    print(sleep_time)
                    sleep(sleep_time)
                    with EmailBox() as email_box:
                        status , emails = email_box.get_mails('Inbox')
                    print(emails)
                    index_list = [mail.mail_id for mail in emails]
                    if status != 'OK':
                        self.stop = True

                    new_mails = [Email(uid) for uid in (set(index_list) - set(start_index_list))]
                    removed_mails = [Email(uid) for uid in (set(start_index_list) - set(index_list))]
                    current_time = datetime.now()
                    if new_mails:
                        self.on_new_event(event=new_mails, event_time = current_time)
                    if removed_mails:
                        self.on_remove_event(event=removed_mails, event_time = current_time)
                        #print('new : ',\
                        #[(self.get_mail_header(id)['from'], self.get_mail_header(id)['subject']) for id in new_mails])
                    start_index_list = index_list
            except KeyboardInterrupt:
                pass

    def _on_new_foo(self, event : list, event_time : datetime) -> None:
        self.events_list.append((f'new at {event_time}', event))

    def _on_remove_foo(self, event : list, event_time : datetime) -> None:
        self.events_list.append((f'remove at {event_time}', event))

class EmailProcessor(multiprocessing.Process):

    class FilterDone(Exception):
        pass

    def __init__(self, email : Email):
        super(EmailProcessor, self).__init__()
        self.email = email
        self.filters_file = 'filters.yaml'
        self.tmp_filters = [{
            "element" : "subject",
            "content" : "email to move",
            "command" : {"action" : "move_email", "attributs" : "Trash"},
            "mark" : "no change"
        },
        {
            "element" : "from",
            "content" : "alien125@g.pl",
            "command" : {"action" : "delete_email", "attributs" : None},
            "mark" : "no change"
        }]
        print('process init')

    def run(self):
        print('process run')
        # mail_header = self.email.get_mail_header()
        # self.email.mark_as_unseen()
        # if mail_header['subject'] == 'move':
        #     print('matching')
        #     self.email.move_email(folder = 'Trash')
        filters = open(self.filters_file)
        for process_filter in self.get_filters(filters):
            try:
                self.filter_email(process_filter)
            except self.FilterDone:
                break
            finally:
                filters.close()

    def get_filters(self, filter_file):
        return yaml.safe_load_all(filter_file)

    def filter_email(self, filter : dict):
        if filter['content'] in self.email.header[filter['element']]:
            self.execute_filter(filter['command'])


    def execute_filter(self, command):
        try:
            getattr(self.email, command['action'])(command['attributs'])
        except Exception as err:
            print(err)
        else:
            raise self.FilterDone

    def __del__(self):
        print('del ', self)

def filter_starter(event, event_time):
    for email in event:
        email_filter = EmailProcessor(email)
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

    for process in multiprocessing.active_children():
            process.join()
