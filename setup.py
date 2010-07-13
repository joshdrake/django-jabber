from distutils.core import setup


setup(
    name="django-jabber",
    version=__import__("jabber").__version__,
    description="""A reusable Django app for queuing the sending of jabber messages,
basically cloned from django-mailer until find time to create a generic messaging
application or fork django-mailer to add XMPP support.""",
    packages=[
        "jabber",
        "jabber.management",
        "jabber.management.commands",
    ],
    package_dir={"jabber": "jabber"},
)
