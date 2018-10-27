from django.conf.urls import url
from filler import views


urlpatterns = [
    url(r'^task/$', views.TaskView.as_view()),
    url(r'^status/$', views.StatusView.as_view()),
    url(r'^process/$', views.ProcessView.as_view()),
    url(r'^games/$', views.FillerGameList.as_view()),
    url(r'^streamers/$', views.FillerStreamerList.as_view()),
    url(r'^custom_queue_status/$', views.CustomQueueStatusList.as_view()),
    url(r'^custom_queue_status/(?P<pk>[0-9]+)$', views.CustomQueueStatusDetail.as_view()),
    url(r'^game_queue_status/$', views.GameQueueStatusList.as_view()),
    url(r'^game_queue_status/(?P<pk>[0-9]+)$', views.GameQueueStatusDetail.as_view())
]
