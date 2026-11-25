from django.urls import include, path
from . import views

app_name = "accounts"
urlpatterns = [
    path("team/", views.TeamListView.as_view(), name="team_list"),
    path("team/new/", views.TeamCreateView.as_view(), name="team_create"),
    path("team/<int:pk>/toggle/", views.TeamToggleActiveView.as_view(), name="team_toggle"),
    path("", include("django.contrib.auth.urls")),   # login, logout, password change
]
