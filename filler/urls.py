from django.conf.urls import url
from filler import views


urlpatterns = [
    url(r'^jobs_available/$', views.JobsAvailableView.as_view()),
    url(r'^status/$', views.StatusView.as_view()),
    url(r'^request_jobs/$', views.RequestJobs.as_view()),
    url(r'^cancel_jobs/$', views.CancelJobs.as_view()),
    url(r'^fake_jobs/$', views.FakeJobs.as_view()),
    url(r'^clear_jobs/$', views.ClearJobs.as_view()),
    url(r'^games/$', views.FillerGameList.as_view()),
    url(r'^streamers/$', views.FillerStreamerList.as_view()),
    url(r'^video/$', views.VideoList.as_view()),
    url(r'^video/(?P<pk>[0-9]+)$', views.VideoDetail.as_view()),
    url(r'^candidate/$', views.CandidateList.as_view()),
    url(r'^candidate/(?P<pk>[0-9]+)$', views.CandidateDetail.as_view()),
]
