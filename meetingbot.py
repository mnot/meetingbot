#!/usr/bin/env python3

import asyncio
from collections import defaultdict
import configparser
import locale

import aioxmpp.muc
import aioxmpp.structs

from framework import Example, exec_example


NO_HISTORY = aioxmpp.muc.xso.History(maxstanzas=0)


class MeetingBot(Example):
    def __init__(self):
        super().__init__()
        self.muc_nick = None
        self.muc_jid = None
        self.room = None
        self.room_future = None
        self.queue = []
        self.hummer = Hummer(self)
        self.helper = Helper(self)

    def prepare_argparse(self):
        super().prepare_argparse()

        language_name = locale.getlocale()[0]
        if language_name == "C":
            language_name = "en-gb"

        def language_range(s):
            return aioxmpp.structs.LanguageRange.fromstr(s.replace("_", "-"))

        default_language = language_range(language_name)

        self.argparse.add_argument(
            "--language",
            default=language_range(language_name),
            type=language_range,
            help="Preferred language: if messages are sent with "
            "multiple languages, this is the language shown "
            "(default: {})".format(default_language),
        )

        # this gives a nicer name in argparse errors
        def jid(s):
            return aioxmpp.JID.fromstr(s)

        self.argparse.add_argument(
            "--muc", type=jid, default=None, help="JID of the muc to join"
        )

        self.argparse.add_argument("--nick", default=None, help="Nick name to use")

    def configure(self):
        super().configure()

        self.language_selectors = [
            self.args.language,
            aioxmpp.structs.LanguageRange.fromstr("*"),
        ]

        self.muc_jid = self.args.muc
        if self.muc_jid is None:
            try:
                self.muc_jid = aioxmpp.JID.fromstr(
                    self.config.get("meetingbot", "muc_jid")
                )
            except (configparser.NoSectionError, configparser.NoOptionError):
                self.muc_jid = aioxmpp.JID.fromstr(input("MUC JID> "))

        self.muc_nick = self.args.nick
        if self.muc_nick is None:
            try:
                self.muc_nick = self.config.get("meetingbot", "nick")
            except (configparser.NoSectionError, configparser.NoOptionError):
                self.muc_nick = input("Nickname> ")

    def make_simple_client(self):
        client = super().make_simple_client()
        muc = client.summon(aioxmpp.MUCClient)
        self.room, self.room_future = muc.join(
            self.muc_jid, self.muc_nick, history=NO_HISTORY
        )
        self.room.on_message.connect(self._on_message)
        return client

    def _on_message(self, message, member, source, **kwargs):
        body = message.body.lookup(self.language_selectors).strip()
        try:
            firstword, rest = body.split(None, 1)
        except ValueError:
            firstword = body
            rest = ""
        firstword = firstword.lower()
        nick = member.nick
        if firstword == "help":
            self.helper.handle_message(rest, nick, message)
        elif firstword == "hum":
            self.hummer.handle_message(rest, nick, message)
        elif firstword in ["q+", "+q"]:
            if rest:
                if rest in self.queue:
                    self.send_reply(message, f"{rest} is already in the queue.")
                    return
                self.queue.append(rest)
                self.send_reply(message, f"{rest} has been queued.")
                return
            elif nick in self.queue:
                self.send_reply(message, f"{nick}, you're already in the queue.")
                return
            self.queue.append(nick)
        elif firstword in ["q-", "-q"]:
            try:
                self.queue.remove(nick)
            except ValueError:
                self.send_reply(message, f"Sorry, {nick} is not in the queue.")
                return
            if rest == "later":
                self.queue.append(nick)
        elif firstword in ["q?", "?q"]:
            self.show_queue(message)
        elif firstword in ["ack"]:
            if not self.queue:
                pass
            elif not rest:
                self.queue.pop(0)
            else:
                try:
                    self.queue.remove(rest)
                except ValueError:
                    self.send_reply(
                        message, f"Sorry, I couldn't find {rest} in the queue."
                    )
            self.show_queue(message)
        else:
            pass

    def show_queue(self, message):
        if self.queue:
            self.send_reply(message, f"The queue is currently: {', '.join(self.queue)}")
        else:
            self.send_reply(message, f"The queue is currently empty.")

    def send_reply(self, to_msg, text):
        reply = to_msg.make_reply()
        reply.body[None] = text
        if self.room:
            self.room.send_message(reply)

    @asyncio.coroutine
    def run_example(self):
        self.stop_event = self.make_sigint_event()
        yield from super().run_example()

    @asyncio.coroutine
    def run_simple_example(self):
        print("waiting to join room...")
        done, pending = yield from asyncio.wait(
            [self.room_future, self.stop_event.wait(),],
            return_when=asyncio.FIRST_COMPLETED,
        )
        if self.room_future not in done:
            self.room_future.cancel()
            return

        for fut in pending:
            fut.cancel()

        yield from self.stop_event.wait()


class Command:
    def __init__(self, bot):
        self.bot = bot

    def handle_message(self, rest, nick, message):
        if not rest:
            self.handle_other("", "", nick, message)
        else:
            try:
                command, rest = rest.split(None, 1)
            except ValueError:
                command = rest
                rest = ""
            if hasattr(self, f"on_{command}"):
                replies = getattr(self, f"on_{command}")(rest)
                for reply in replies:
                    self.bot.send_reply(message, reply)
            else:
                self.handle_other(command, rest, nick, message)

    def handle_other(self, command, rest, nick, message):
        raise NotImplementedError


class Helper(Command):
    def handle_other(self, command, rest, nick, message):
        self.bot.send_reply(
            message,
            f"To get help, type 'help _command_'. I can give help about 'queue' and \
'hum', and 'about' currently.",
        )

    def on_queue(self, rest):
        return [
            f"Use 'q+' to add yourself to the queue. To add someone else, use 'q+ _nick_'.",
            f"Use 'q-' to remove yourself. 'q- later' moves you to the end of the queue.",
            f"Use 'ack' acknowledge the first queued person when they speak. Use 'ack _nick_' to acknowledge someone else.",
            f"Use 'q?' to see the current contents of the queue.",
        ]

    def on_q(self, rest):
        return self.on_queue(rest)

    def on_hum(self, rest):
        return [
            f"To hum: set a topic with 'hum topic _topic_', then add options with 'hum option \
_description_'.",
            f"Start the hum with 'hum start', and conclude with 'hum stop'."
        ]

    def on_about(self, rest):
        return [
            f"Hi, I'm meetingbot. You can learn more about me at <https://github.com/mnot/meetingbot>."
        ]


class Hummer(Command):
    def __init__(self, bot):
        Command.__init__(self, bot)
        self.init_hum()

    def init_hum(self):
        self.humming = False
        self.hum_topic = ""
        self.hum_options = []
        self.hum_results = {}

    def handle_other(self, command, rest, nick, message):
        if (
            self.humming
            and command.isdigit()
            and 0 < int(command) <= len(self.hum_options)
        ):
            self.hum_results[nick] = int(command)
        elif self.humming:
            self.bot.send_reply(
                message, f"{nick}, '{command}' is not an option. Please try again."
            )
        else:
            self.bot.send_reply(message, f"I don't understand '{command}', {nick}.")

    def on_topic(self, rest):
        if not rest:
            return ["Please provide a hum topic."]
        if self.humming:
            return ["Sorry, topic can't be changed during the hum."]
        self.hum_topic = rest
        return ["Topic set."]

    def on_option(self, rest):
        if not rest:
            return ["Please provide a hum option description."]
        if self.humming:
            return ["Sorry, options can't be changed during the hum."]
        self.hum_options.append(rest)
        return [f"Option {len(self.hum_options)} recorded."]

    def on_start(self, rest):
        if self.humming:
            return [f"Sorry, there's already a hum running."]
        if not self.hum_topic:
            return [f"Please set a hum topic with 'hum topic _topic_'."]
        if len(self.hum_options) < 2:
            return [
                f"Please set at least two hum options with 'hum option _description_'."
            ]
        self.humming = True
        replies = [f"* Starting hum: {self.hum_topic}"]
        i = 1
        for option in self.hum_options:
            replies.append(f"  Option {i}: {option}")
            i += 1
        replies.append(
            f"Please hum like this: 'hum n' for option n. To finish, 'hum stop'."
        )
        return replies

    def on_stop(self, rest):
        if not self.humming:
            return [f"Sorry, there isn't a hum running."]
        self.humming = False
        results = defaultdict(int)
        for hum in self.hum_results.values():
            results[hum] += 1
        replies = ["* Finishing hum. The results are:"]
        replies.append(self.hum_topic)
        i = 1
        for option in self.hum_options:
            replies.append(f"  Option {i}: {option} -- {results[i]} hummed")
            i += 1
        self.init_hum()
        return replies


if __name__ == "__main__":
    exec_example(MeetingBot())
