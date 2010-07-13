import logging
import pickle

from datetime import datetime

import xmpp

from django.db import models

PRIORITIES = (
    ("1", "high"),
    ("2", "medium"),
    ("3", "low"),
    ("4", "deferred"),
)

class XMPPConnectionError(Exception):
    pass

class JabberMessage(object):
    def __init__(self, subject="", body="", from_jid=None, to=None):
        self.subject = subject
        self.body = body
        self.from_jid = from_jid
        self.to = to

    def send(self, fail_silently=False):
        if self.connection:
            try:
                for recipient in self.to:
                    self.connection.send(xmpp.protocol.Message(recipient, '%s: %s' % (self.subject, self.body)))
            except:
                if not fail_silently:
                    raise
        else:
            raise XMPPConnectionError('No XMPP connection provided')

class MessageManager(models.Manager):
    
    def high_priority(self):
        """
        the high priority messages in the queue
        """
        
        return self.filter(priority="1")
    
    def medium_priority(self):
        """
        the medium priority messages in the queue
        """
        
        return self.filter(priority="2")
    
    def low_priority(self):
        """
        the low priority messages in the queue
        """
        
        return self.filter(priority="3")
    
    def non_deferred(self):
        """
        the messages in the queue not deferred
        """
        
        return self.filter(priority__lt="4")
    
    def deferred(self):
        """
        the deferred messages in the queue
        """
    
        return self.filter(priority="4")
    
    def retry_deferred(self, new_priority=2):
        count = 0
        for message in self.deferred():
            if message.retry(new_priority):
                count += 1
        return count


class Message(models.Model):
    
    message_data = models.TextField()
    when_added = models.DateTimeField(default=datetime.now)
    priority = models.CharField(max_length=1, choices=PRIORITIES, default="2")
    
    objects = MessageManager()
    
    def defer(self):
        self.priority = "4"
        self.save()
    
    def retry(self, new_priority=2):
        if self.priority == "4":
            self.priority = new_priority
            self.save()
            return True
        else:
            return False
    
    def _get_message(self):
        if self.message_data == "":
            return None
        else:
            return pickle.loads(self.message_data.encode("ascii"))
    
    def _set_message(self, val):
        self.message_data = pickle.dumps(val)
    
    message = property(_get_message, _set_message, doc=
                     """JabberMessage object. If this is mutated, you will need to
set the attribute again to cause the underlying serialised data to be updated.""")
    
    @property
    def to_addresses(self):
        message = self.message
        if message is not None:
            return message.to
        else:
            return []
    
    @property
    def subject(self):
        message = self.message
        if message is not None:
            return message.subject
        else:
            return ""


def filter_recipient_list(lst):
    if lst is None:
        return None
    retval = []
    for e in lst:
        if DontSendEntry.objects.has_address(e):
            logging.info("skipping message to %s as on don't send list " % e.encode("utf-8"))
        else:
            retval.append(e)
    return retval


def make_message(subject="", body="", from_jid=None, to=None, priority=None):
    """
    Creates a simple message for the parameters supplied.
    The 'to' and 'bcc' lists are filtered using DontSendEntry.
    
    If needed, the 'message' attribute can be set to any instance of JabberMessage.
    
    Call 'save()' on the result when it is ready to be sent, and not before.
    """
    to = filter_recipient_list(to)
    core_msg = JabberMessage(subject=subject, body=body, from_jid=from_jid, to=to)

    db_msg = Message(priority=priority)
    db_msg.message = core_msg
    return db_msg


class DontSendEntryManager(models.Manager):
    
    def has_address(self, address):
        """
        is the given address on the don't send list?
        """
        
        if self.filter(to_address__iexact=address).exists():
            return True
        else:
            return False


class DontSendEntry(models.Model):
    
    to_address = models.EmailField()
    when_added = models.DateTimeField()
    # @@@ who added?
    # @@@ comment field?
    
    objects = DontSendEntryManager()
    
    class Meta:
        verbose_name = "don't send entry"
        verbose_name_plural = "don't send entries"


RESULT_CODES = (
    ("1", "success"),
    ("2", "don't send"),
    ("3", "failure"),
    # @@@ other types of failure?
)


class MessageLogManager(models.Manager):
    
    def log(self, message, result_code, log_message=""):
        """
        create a log entry for an attempt to send the given message and
        record the given result and (optionally) a log message
        """
        
        message_log = self.create(
            message_data = message.message_data,
            when_added = message.when_added,
            priority = message.priority,
            # @@@ other fields from Message
            result = result_code,
            log_message = log_message,
        )
        message_log.save()


class MessageLog(models.Model):
    
    # fields from Message
    message_data = models.TextField()
    when_added = models.DateTimeField()
    priority = models.CharField(max_length=1, choices=PRIORITIES)
    # @@@ campaign?
    
    # additional logging fields
    when_attempted = models.DateTimeField(default=datetime.now)
    result = models.CharField(max_length=1, choices=RESULT_CODES)
    log_message = models.TextField()
    
    objects = MessageLogManager()
    
    @property
    def message(self):
        if self.message_data == "":
            return None
        else:
            return pickle.loads(self.message_data.encode("ascii"))
    
    @property
    def to_addresses(self):
        message = self.message
        if message is not None:
            return message.to
        else:
            return []
    
    @property
    def subject(self):
        message = self.message
        if message is not None:
            return message.subject
        else:
            return ""
