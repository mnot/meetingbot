
# Meetingbot

This is a fairly quick XMPP bot to help run meetings. It can:

* Manage a queue of speakers
* Take a virtual "hum" -- i.e., sense of the room / vote

It requires Python 3 and [aioxmpp](https://pypi.org/project/aioxmpp/).

To run it, use a command line like this:

> ./meetingbot.py -j meetingbot@mnot.net -p --muc meetingbot-test@chat.mnot.net --nick meetingbot

Once it's joined the channel, type `help` for available commands.