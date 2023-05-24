from df_chat.drf.serializers import MessageSerializer
from df_chat.models import RoomUser, Room
from rest_framework.exceptions import  PermissionDenied
from channels.db import database_sync_to_async


class AsyncMessageSerializer(MessageSerializer):
    def _get_room_user(self):
        user = self.context["scope"]["user"]
        room_id = self.context["room_id"]

        rooms_accessible_to_user = Room.objects.filter_for_user(user)
        if not (room_id and rooms_accessible_to_user.filter(id=room_id).exists()):
            raise PermissionDenied("user doesn't have access to room")
        
        return RoomUser.objects.get_room_user(
            room_pk=room_id,
            user_pk=user.id,
        )
    
    @database_sync_to_async
    def is_valid(self, *, raise_exception=False):
        return super().is_valid(raise_exception=raise_exception)
    
    @database_sync_to_async
    def save(self, **kwargs):
        return super().save(**kwargs)
