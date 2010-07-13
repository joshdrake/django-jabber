import logging

from django.core.management.base import NoArgsCommand

from jabber.models import Message


class Command(NoArgsCommand):
    help = "Attempt to resend any deferred messages."
    
    def handle_noargs(self, **options):
        logging.basicConfig(level=logging.DEBUG, format="%(message)s")
        count = Message.objects.retry_deferred() # @@@ new_priority not yet supported
        logging.info("%s message(s) retried" % count)
