from django.urls import path

from cl.research_sync import views

app_name = "research_sync"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("hit/<int:hit_id>/read/", views.mark_read, name="mark_read"),
]
