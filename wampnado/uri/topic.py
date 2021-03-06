"""
Classes and methods for Topic URIs for pub/sub
"""

from inspect import isfunction
from warnings import warn

import tornadis
from tornado import ioloop
from tornado.websocket import WebSocketClosedError

from wampnado.uri import URI, URIType
from wampnado.features import Options, server_features
from wampnado.identifier import create_global_id
from wampnado.auth import server_auth_ident
from wampnado.messages import PublishedMessage, EventMessage

PUBSUB_TIMEOUT = 60
PUBLISHER_CONNECTION_TIMEOUT = 3 * 3600 * 1000  # 3 hours in miliseconds

class Subscriber:
    def __init__(self, handler):
        self.subscription_id = create_global_id()

        if isfunction(handler):
            self.pseudo = True
            self.callback = handler
        else:
            self.pseudo = False
            self.handler = handler

    def write_message(self, msg):
        self.handler.write_message(msg)

    @property
    def sessionid(self):
        if self.pseudo:
            return server_auth_ident.sessionid
        else:
            return self.handler.sessionid


class Topic(URI):
    """
    A uri URI for use with pub/sub functionality.
    """

    def __init__(self, name, reserver=None):
        """

        """
        super().__init__(name, URIType.TOPIC)
        self.subscribers = {}
        self.reserver = reserver
        self.registration_id = create_global_id()

    def publish(self, origin_handler, broadcast_msg):
        """
        Publish broadcast_msg to all subscribers.

        "By default, publications are unacknowledged, and the Broker will not respond, whether the publication was successful indeed or not. This behavior can be changed with the option PUBLISH.Options.acknowledge|bool (see below)."
        --https://wamp-proto.org/_static/gen/wamp_latest.html

        """
        publication_id = create_global_id()

        purge = []

        for subscription_id in self.subscribers.keys():
            try:
                if self.subscribers[subscription_id].pseudo:
                    # We expect all pseudo-subscribers to accept any provided parameters, or accept the output to the error log.
                    self.subscribers[subscription_id].callback(*broadcast_msg.args, **broadcast_msg.kwargs)                     
                else:
                    event_message = EventMessage(subscription_id=subscription_id, publication_id=publication_id, args=broadcast_msg.args, kwargs=broadcast_msg.kwargs)

                    # Per WAMP standard, the publisher does not receive the message.
                    if origin_handler is None or self.subscribers[subscription_id].sessionid != origin_handler.sessionid:
                        self.subscribers[subscription_id].write_message(event_message)

            # If we get an error, remove the subscription.
            except WebSocketClosedError:
                purge.append(subscription_id)

        # We don't do this until the loop is done to prevent breaking the iterator.
        for subscription_id in purge:
            del self.subscribers[subscription_id]

        if broadcast_msg.options.acknowlege:
            return PublishedMessage(request_id=broadcast_msg.request_id, publication_id=self.registration_id)
        else:
            return None
            

    def remove_subscriber(self, handler):
        """
        Removes subscriber from uri.
        """
        if handler.sessionid in self.subscribers:
            return self.subscribers.pop(handler.sessionid)

    def add_subscriber(self, handler):
        """
        Add subscriber to a uri.
        """
        sub = Subscriber(handler)
        self.subscribers[sub.subscription_id] = sub

        return sub.subscription_id


    def disconnect(self, handler):
        """
        Removes a given handler from any role in the uri.
        """
        if self.reserver is not None and self.reserver == handler:
            self.reserver = None
        self.remove_subscriber(handler)

    @property
    def live(self):
        if len(self.subscribers.keys()) > 0:
            return True
        else:
            return False

