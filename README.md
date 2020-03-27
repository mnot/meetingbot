
# Meetingbot

This is an XMPP bot to help run meetings. It can:

* Manage a queue of speakers (with "q+", "q-", etc.)
* Take a virtual "hum" -- i.e., sense of the room / vote

It is inspired by the W3C's [Zakim](https://www.w3.org/2001/12/zakim-irc-bot.html).

## Setup

Before you start your meeting:

* Clone or download the [meetingbot project](https://github.com/mnot/meetingbot),
* Make sure you have Python 3,
* Install [aioxmpp](https://pypi.org/project/aioxmpp/) (e.g., `pip3 install aioxmpp`), and
* Create a jabber account for your bot.

To run it, use a command line like this:

> ./meetingbot.py -j meetingbot@mnot.net -p --muc meetingbot-test@chat.mnot.net --nick meetingbot

... where `-j` gives the Jabber ID of the account that meetingbot will log in as (the password will be asked for, thanks to `-p`). `--muc` gives the name of the chat room that it will join, and `--nick` is the nickname it will use.

Once it's joined the channel, type `help` for available commands.
