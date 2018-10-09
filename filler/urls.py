from django.conf.urls import url
from filler import views


urlpatterns = [
    url(r'^jobs_available/$', views.JobsAvailableView.as_view()),
    url(r'^status/$', views.StatusView.as_view()),
    url(r'^request_jobs/$', views.RequestJobs.as_view()),
    url(r'^cancel_jobs/$', views.CancelJobs.as_view()),
    url(r'^clear_jobs/$', views.ClearJobs.as_view()),
    url(r'^custom_queue_status/$', views.CustomQueueStatusList.as_view()),
    url(r'^custom_queue_status/(?P<pk>[0-9]+)$', views.CustomQueueStatusDetail.as_view()),
    url(r'^game_queue_status/$', views.GameQueueStatusList.as_view()),
    url(r'^game_queue_status/(?P<pk>[0-9]+)$', views.GameQueueStatusDetail.as_view()),
    url(r'^games/$', views.FillerGameList.as_view()),
    url(r'^streamers/$', views.FillerStreamerList.as_view()),
    url(r'^video/$', views.VideoList.as_view()),
    url(r'^video/(?P<pk>[0-9]+)$', views.VideoDetail.as_view()),
]
