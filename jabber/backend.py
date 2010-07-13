from jabber.models import Message


class DbBackend(object):
    
    def send_messages(self, jabber_messages):
        num_sent = 0
        for message in jabber_messages:
            msg = Message()
            msg.message = message
            msg.save()
            num_sent += 1
        return num_sent
