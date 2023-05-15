from django.contrib import admin
from django.urls import include
from django.urls import path


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/chat/", include("df_chat.drf.urls")),
    path("api/v1/auth/", include("df_auth.drf.urls")),
    path("chat/", include("df_chat.urls")),
]
