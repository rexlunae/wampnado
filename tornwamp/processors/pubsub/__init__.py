"""
WAMP-PubSub processors.
"""
from tornwamp.identifier import create_global_id
from tornwamp.messages import ErrorMessage, EventMessage, PublishMessage, PublishedMessage, SubscribeMessage, SubscribedMessage
from tornwamp.processors import Processor
from tornwamp.processors.pubsub import customize


class SubscribeProcessor(Processor):
    """
    Responsible for dealing SUBSCRIBE messages.
    """
    def process(self):
        """
        Return SUBSCRIBE message based on the input HELLO message.
        """
        received_message = SubscribeMessage(*self.message.value)
        allow, msg = customize.authorize_subscription(received_message.topic, self.connection)
        if allow:
            new_id = customize.add_subscriber(received_message.topic, self.connection)
            answer = SubscribedMessage(
                request_id=received_message.request_id,
                subscription_id=new_id
            )
        else:
            answer = ErrorMessage(
                request_id=received_message.request_id,
                request_code=received_message.code,
                uri="tornwamp.subscribe.unauthorized"
            )
            answer.error(msg)
        self.answer_message = answer


class PublishProcessor(Processor):
    """
    Responsible for dealing SUBSCRIBE messages.
    """
    def process(self):
        """
        Return SUBSCRIBE message based on the input HELLO message.
        """
        received_message = PublishMessage(*self.message.value)
        allow, msg = customize.authorize_publication(received_message.topic, self.connection)
        if allow:
            publication_id = create_global_id()
            answer = PublishedMessage(
                request_id=received_message.request_id,
                publication_id=publication_id
            )
            self.direct_messages = customize.get_direct_messages(received_message, publication_id)
        else:
            answer = ErrorMessage(
                request_id=received_message.request_id,
                request_code=received_message.code,
                uri="tornwamp.publish.unauthorized"
            )
            answer.error(msg)
        self.answer_message = answer