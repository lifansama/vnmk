#!/usr/bin/env python3

from threading import Thread, Timer
import time
import requests
import os

from .looptimer import LoopTimer


class TelegramAuthenticateBot:

    """This is a very simple authentication bot like WeChat. The user scans a
    QRCode containing a token. The token as init parameter will be sent via
    user's Telegram to this bot, which will verify that the token is what we
    wanted, and the user is someone we knew. If all works, the bot excites the
    background server. And the server tells all connected clients about that
    incident.

    Although Telegram does provide much simpler process(login widget on web
    page), there're some considerations to prefer using this method:
    
        1. Web login stores cookie, which is used to simplify afterward logins.
        BUT for our application, it's better preferred to ask the user
        authenticate AGAIN, since that will produce a notification on user's
        phone, which is a signal on system being excited. Telegram doesn't
        provide a reliable way to revoke a user's token, making this process
        a bit insecure.
        2. The Telegram javascript for above login contains "eval" in JS, which
        is not much wanted when we want to apply Content Security Policy.
        3. By forcing the user to contact our Bot first, we can notify user
        on further logins actively. (Web login by Telegram may in principle
        have same feature, but currently not works).

    This authentication bot method is different from that by WeChat, in that
    there's no real distinction between each client: We just want to make sure
    the system is excited, "By whom?" is not important. THEREFORE we'll ask all
    users to scan the same token. But anyway, only the users preconfigured in
    YAML can actually excite the system.
    """

    def __init__(self, config):
        """Sends information about system status via Telegram. This class
        checks for system status every 1 minute, and will remind the user
        of excited status every 5 minutes from the first excitation."""
        self.config = config
        self.sending = False
        self.apiURL = \
            lambda i: "https://api.telegram.org/bot%s/%s" % (config["token"], i)
        self.__pollNext = False
        self.__lastUpdateID = 0

        self.__recognizedTokens = []
        self.__tokenRotater = LoopTimer(self.__rotateToken, interval=30)

        self.onTokenVerified = lambda: None 
        self.statemanager = None

    def __rotateToken(self):
        """Generates a new token for login, and revoke an old one."""
        self.__recognizedTokens.append(os.urandom(16).hex())
        if len(self.__recognizedTokens) > 2:
            self.__recognizedTokens = self.__recognizedTokens[-2:]

    @property
    def token(self):
        return self.__recognizedTokens[-1]

    def __processUpdateMessage(self, message):
        """
        {'message_id': 2, 'from': {'id': *****, 'is_bot': False,
        'first_name': 'NeoAtlantis', 'username': 'NeoAtlantis',
        'language_code': 'de-DE'}, 'chat': {'id': ****, 'first_name':
        'NeoAtlantis', 'username': 'NeoAtlantis', 'type': 'private'}, 'date':
        ****, 'text': 'hi'}"""
        msgFrom = message["from"]
        msgChat = message["chat"]
        if msgFrom["username"] not in self.config["users"]: return
        if msgFrom["is_bot"]: return
        if msgChat["type"] != "private": return
        if "text" not in message: return
        if "date" not in message: return
        text, date = message["text"], message["date"]
        if text.startswith("/start"):
            token = text[6:].strip()
            if token and token in self.__recognizedTokens:
                print("Token is valid.")
                self.onTokenVerified()

    def __pollUpdate(self):
        if not self.__pollNext: return
        interval = 0

        updates = []
        try:
            url = self.apiURL("getUpdates")
            req = requests.get(
                url,
                data={"offset": self.__lastUpdateID+1},
                timeout=5
            )
            assert req.status_code == 200
            json = req.json()
            assert json["ok"]
            updates = json["result"]
        except Exception as e:
            print("Failed pulling updates from telegram. Wait 5 seconds...")
            interval = 5

        for update in updates:
            try:
                update_id = update["update_id"]
                message = update["message"]
                self.__lastUpdateID = max(update_id, self.__lastUpdateID)
                self.__processUpdateMessage(message)
            except Exception as e:
                print(e)
        
        if self.__pollNext:
            self.pollThread = Timer(interval, self.__pollUpdate)
            self.pollThread.start()

    def __enter__(self, *args):
        self.__tokenRotater.start()
        self.__pollNext = True
        self.pollThread = Thread(target=self.__pollUpdate)
        self.pollThread.start()
        return self

    def __exit__(self, *args):
        self.__tokenRotater.stop()
        self.__pollNext = False

    def __telegramSendMessage(self):
        pass

    def __sendMessage(self):
        if self.sending: return
        self.sending = True
        try:
            for i in range(0, 5):
                pass
        finally:
            self.sending = False
