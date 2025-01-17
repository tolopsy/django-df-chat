from df_chat.tests.base import BaseTestUtilsMixin
from django.urls import reverse
from rest_framework.test import APITestCase


class TestMessageEndpoint(APITestCase, BaseTestUtilsMixin):
    """
    Testing the RESTful API messages endpoint
    """

    def test_message_creation_success(self):
        """
        Testing creation of a message using the messages endpoint.
        """
        user, token = self.create_user()
        room = self.create_room_and_add_users(user)

        message_endpoint = reverse("rooms-messages-list", kwargs={"room_pk": room.pk})
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + token)
        response = self.client.post(message_endpoint, {"body": "Hi"})
        message = response.json()

        room_user = user.roomuser_set.get()
        self.assertEqual(message["body"], "Hi")
        self.assertTrue(message["is_me"])
        self.assertEqual(message["room_user_id"], room_user.pk)
        self.assertIsNone(message["parent_id"])
        self.assertFalse(message["is_reaction"])

    # TODOS: We should also implement the following tests:
    # - Fail to create a message when the user is not authenticated.
    # - Ensure that the endpoint returns a 404 error
    #   - if the user is not part of a Room
    #   - if a room doesn't exist at all.
