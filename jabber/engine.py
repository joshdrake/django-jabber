import time
import xmpp
import logging
from socket import error as socket_error

from lockfile import FileLock, AlreadyLocked, LockTimeout

from django.conf import settings

from jabber.models import Message, DontSendEntry, MessageLog, XMPPConnectionError


# when queue is empty, how long to wait (in seconds) before checking again
EMPTY_QUEUE_SLEEP = getattr(settings, "JABBER_EMPTY_QUEUE_SLEEP", 30)

# lock timeout value. how long to wait for the lock to become available.
# default behavior is to never wait for the lock to be available.
LOCK_WAIT_TIMEOUT = getattr(settings, "JABBER_LOCK_WAIT_TIMEOUT", -1)

class XMPPAuthenticationFailure(Exception):
    pass

def get_connection(jid, password):
    jid = xmpp.protocol.JID(jid)    
    client = xmpp.Client(jid.getDomain(), debug=[])
    client.connect()
    if not client.auth(jid.getNode(), password, resource=jid.getResource()):
        raise XMPPAuthenticationFailure("Unable to authenticate JID %s" % jid)
    return client

def prioritize():
    """
    Yield the messages in the queue in the order they should be sent.
    """
    
    while True:
        while Message.objects.high_priority().count() or Message.objects.medium_priority().count():
            while Message.objects.high_priority().count():
                for message in Message.objects.high_priority().order_by("when_added"):
                    yield message
            while Message.objects.high_priority().count() == 0 and Message.objects.medium_priority().count():
                yield Message.objects.medium_priority().order_by("when_added")[0]
        while Message.objects.high_priority().count() == 0 and Message.objects.medium_priority().count() == 0 and Message.objects.low_priority().count():
            yield Message.objects.low_priority().order_by("when_added")[0]
        if Message.objects.non_deferred().count() == 0:
            break


def send_all():
    """
    Send all eligible messages in the queue.
    """
    lock = FileLock("send_mail")
    
    logging.debug("acquiring lock...")
    try:
        lock.acquire(LOCK_WAIT_TIMEOUT)
    except AlreadyLocked:
        logging.debug("lock already in place. quitting.")
        return
    except LockTimeout:
        logging.debug("waiting for the lock timed out. quitting.")
        return
    logging.debug("acquired.")
    
    start_time = time.time()
    
    dont_send = 0
    deferred = 0
    sent = 0
    
    try:
        connection = None
        for message in prioritize():
            try:
                if connection is None:
                    connection = get_connection(settings.JABBER_JID, settings.JABBER_PASSWORD)
                logging.info("sending message '%s' to %s" % (message.subject.encode("utf-8"), u", ".join(message.to_addresses).encode("utf-8")))
                jabber = message.message
                jabber.connection = connection
                jabber.send()
                MessageLog.objects.log(message, 1) # @@@ avoid using literal result code
                message.delete()
                sent += 1
            except (socket_error, XMPPAuthenticationFailure, XMPPConnectionError), err:
                message.defer()
                logging.info("message deferred due to failure: %s" % err)
                MessageLog.objects.log(message, 3, log_message=str(err)) # @@@ avoid using literal result code
                deferred += 1
                # Get new connection, it case the connection itself has an error.
                connection = None
    finally:
        logging.debug("releasing lock...")
        lock.release()
        logging.debug("released.")
    
    logging.info("")
    logging.info("%s sent; %s deferred;" % (sent, deferred))
    logging.info("done in %.2f seconds" % (time.time() - start_time))

def send_loop():
    """
    Loop indefinitely, checking queue at intervals of EMPTY_QUEUE_SLEEP and
    sending messages if any are on queue.
    """
    
    while True:
        while not Message.objects.all():
            logging.debug("sleeping for %s seconds before checking queue again" % EMPTY_QUEUE_SLEEP)
            time.sleep(EMPTY_QUEUE_SLEEP)
        send_all()
