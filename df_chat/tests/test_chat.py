from channels.db import database_sync_to_async

# The WebsocketCommunicator provides convenient methods to simplify the process of connecting to a websocket.
from channels.testing import WebsocketCommunicator
from df_chat.models import Message
from df_chat.models import RoomUser
from df_chat.tests.utils import RoomFactory
from df_chat.tests.utils import TEST_USER_PASSWORD
from df_chat.tests.utils import UserFactory
from django.test import TransactionTestCase
from rest_framework.reverse import reverse
from tests.asgi import application
from uuid import uuid4


class TestChat(TransactionTestCase):
    """
    Test for chat appplication
    """

    def setUp(self):
        # Let's setup a room with two users in it.
        self.room = RoomFactory()
        self.user1 = UserFactory()
        self.user2 = UserFactory()
        self.room.users.set([self.user1, self.user2])

        # Each user has to use an authentication token in order to connect with the websocket endpoint.
        # So, lets generate and store them in attributes.
        auth_token_url = reverse("token-list")
        response = self.client.post(
            auth_token_url,
            data={"username": self.user1.username, "password": TEST_USER_PASSWORD},
        )
        self.token1 = response.json()["token"]
        response = self.client.post(
            auth_token_url,
            data={"username": self.user2.username, "password": TEST_USER_PASSWORD},
        )
        self.token2 = response.json()["token"]

    async def test_invalid_websocket_path(self):
        """
        We should reject the connection, if an invalid route is provided.
        """
        communicator = WebsocketCommunicator(application, "ws/dummy")
        with self.assertRaisesMessage(ValueError, "No route found for path 'ws/dummy'"):
            await communicator.connect()

    async def test_auth(self):
        """
        Ensures that the authenticated user is added to the scope of the websocket consumer.
        """
        communicator = WebsocketCommunicator(
            application, f"ws/chat/?token={self.token1}"
        )
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        # self.token1 belongs to self.user1
        # Checking that our self.user1 was added to the scope.
        self.assertEqual(communicator.scope["user"], self.user1)
        await communicator.disconnect()

    async def test_end_to_end(self):
        """
        An end-to-end test case to test the happy-path-flow of a chat between two users
        """
        # connecting our first user to the chat websocket endpoint
        communicator1 = WebsocketCommunicator(
            application, f"ws/chat/?token={self.token1}"
        )
        await communicator1.connect()

        # As of now, there are no messages in the room
        # The WebsocketCommunicator.receive_nothing returns a True, if there is no message to receive.
        self.assertTrue(await communicator1.receive_nothing())

        #  Lets subscribe user1 to the room, so that the user1 is notified when there is any activity in the room.
        await communicator1.send_json_to(
            {
                "action": "subscribe_to_room_activity",
                "request_id": str(uuid4()),
                "room_pk": str(self.room.id),
            }
        )

        # connecting our second user to the chat websocket endpoint
        communicator2 = WebsocketCommunicator(
            application, f"ws/chat/?token={self.token2}"
        )
        await communicator2.connect()
        #  Also subscribing user2 to the room.
        await communicator2.send_json_to(
            {
                "action": "subscribe_to_room_activity",
                "request_id": str(uuid4()),
                "room_pk": str(self.room.id),
            }
        )

        # When another user connects to a room, the first user will receive a json dict stating that a user
        # has joined the room. Here user2 has subscribed to the room, so user1 will be notified.
        event = await communicator1.receive_json_from()
        room_user2 = await database_sync_to_async(RoomUser.objects.get)(
            room=self.room, user=self.user2
        )
        self.assertEqual(
            event["users"][0],
            {
                "id": room_user2.id,
                "is_me": False,
                "is_online": True,
                "is_active": True,
                "room_id": self.room.id,
            },
        )
        # But, no messages are sent by the second user.
        self.assertEqual(len(event["messages"]), 0)

        room_user1 = await database_sync_to_async(RoomUser.objects.get)(
            room=self.room, user=self.user1
        )

        # If a Message object is created, it should be received by both users
        await database_sync_to_async(Message.objects.create)(
            room_user=room_user1, body="Hi"
        )
        event1 = await communicator1.receive_json_from()
        event2 = await communicator2.receive_json_from()
        # Only one message will be received by each user
        self.assertEqual(len(event1["messages"]), 1)
        self.assertEqual(len(event2["messages"]), 1)
        message_received_by_user1 = event1["messages"][0]
        message_received_by_user2 = event2["messages"][0]
        self.assertEqual(message_received_by_user1["body"], "Hi")
        self.assertEqual(message_received_by_user1["room_id"], self.room.id)
        self.assertEqual(message_received_by_user1["room_user_id"], room_user1.id)
        self.assertEqual(message_received_by_user1["is_me"], True)
        self.assertEqual(message_received_by_user2["is_me"], False)
        # Except for "is_me", everything else in the message is same for both the users
        del message_received_by_user1["is_me"]
        del message_received_by_user2["is_me"]
        self.assertDictEqual(message_received_by_user1, message_received_by_user2)


# TODO: Trying to connect without providing a token results in an error "ValueError: 'AnonymousUser' value must be a positive integer or a valid Hashids string."
# We should return a permission denied message via the websocket and gracefully disconnect the user.
# TODO: In the current approach, in order to create a message in a room, a user should make a HTTP POST request.
# And then the message is propagated to all the listeners in that room.
# But, chatting is done in real-time. Users expect to send and receive messages real quick.
# An HTTP connection not stateful. It takes time to connect. And disconnects immediately once the request is fulfiled.
# On the other hand, a websocket connection is stateful - the connection is live until either party terminates it.
# So, using websockets we could communicate in real time.
# - we should allow users to create messages via websocket instead of HTTP.
