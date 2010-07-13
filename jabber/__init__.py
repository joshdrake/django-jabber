VERSION = (0, 0, 1, "a", 1) # following PEP 386
DEV_N = 1


def get_version():
    version = "%s.%s" % (VERSION[0], VERSION[1])
    if VERSION[2]:
        version = "%s.%s" % (version, VERSION[2])
    if VERSION[3] != "f":
        version = "%s%s%s" % (version, VERSION[3], VERSION[4])
        if DEV_N:
            version = "%s.dev%s" % (version, DEV_N)
    return version


__version__ = get_version()


PRIORITY_MAPPING = {
    "high": "1",
    "medium": "2",
    "low": "3",
    "deferred": "4",
}



def send_jabber(subject, message, from_jid, recipient_list, priority="medium", fail_silently=False):
    from django.utils.encoding import force_unicode
    from jabber.models import make_message
    
    priority = PRIORITY_MAPPING[priority]
    
    # need to do this in case subject used lazy version of ugettext
    subject = force_unicode(subject)
    message = force_unicode(message)
    
    make_message(subject=subject,
                 body=message,
                 from_jid=from_jid,
                 to=recipient_list,
                 priority=priority).save()
    return 1
