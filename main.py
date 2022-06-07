import imaplib
import email
import base64

class Email:
    from config import domian, user, password as _password

    def __init__(self) -> None:
        pass

    def connect(self):
        self.connection = imaplib.IMAP4(self.domian, 993)
        self.connection.login(self.user, self._password)

    def connect_ssl(self):
        self.connection = imaplib.IMAP4_SSL(host=self.domian)
        self.connection.login(self.user, self._password)

    def disconect(self):
        self.connection.close()
        self.connection.logout()

    def get_mails(self, folder = 'INBOX'):
        self.connection.select(folder)
        status, index_list = self.connection.search(None, 'ALL')
        return status, index_list

    def get_mail_content(self, mail_index):
        status, raw_content = self.connection.fetch(mail_index, '(RFC822)')
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

if __name__ == '__main__':
    inbox = Email()

    inbox.domian = 'imap.mail.yahoo.com'
    inbox.user = 'maciej.mkan'
    inbox._password = 'brypeweozlzzonpc'

    inbox.connect_ssl()

    status, index_list = inbox.get_mails()
    if status == 'OK':
        for i in index_list[0].split():
            print(i)
            print(inbox.get_mail_content(i))

    inbox.disconect()
