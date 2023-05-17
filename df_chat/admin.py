from .models import Message
from .models import MessageImage
from .models import Room
from .models import RoomUser
from django.contrib import admin


class RoomUserInline(admin.TabularInline):
    model = RoomUser


class IsOnlineFilter(admin.SimpleListFilter):
    """
    Human-readable title which will be displayed in the
    right admin sidebar just above the filter options in the RoomUser change page.
    """

    title = "is online"

    # Parameter for the filter that will be used in the URL query.
    parameter_name = "is_online"

    def lookups(self, request, model_admin):
        return (
            (True, "Yes"),
            (False, "No"),
        )

    def queryset(self, request, queryset):
        if self.value() == "True":
            return queryset.filter(user__user_chat__is_online=True)
        if self.value() == "False":
            return queryset.filter(user__user_chat__is_online=False)


@admin.register(RoomUser)
class RoomUserAdmin(admin.ModelAdmin):
    list_display = ("room", "user", "is_active", "get_is_online")
    list_filter = ("is_active", "room__title", IsOnlineFilter)

    # Using this, the 'is_online' column on the RoomUser change page in the admin dashboard
    # will display beautiful icons ✅ for online users and ❌ for offline users.
    @admin.display(description="is_online", boolean=True)
    def get_is_online(self, obj: RoomUser) -> bool:
        return obj.is_online


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "creator",
        "created",
    )


class MessageImageInline(admin.TabularInline):
    model = MessageImage


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    def room(self, obj):
        return obj.room_user.room

    list_display = ("room", "body", "room_user", "parent", "created", "modified")
