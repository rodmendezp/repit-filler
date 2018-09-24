from django.conf.urls import url
from filler import views


urlpatterns = [
    url(r'^jobs_available/$', views.JobsAvailableView.as_view()),
    url(r'^status/$', views.StatusView.as_view()),
    url(r'^request_jobs/$', views.RequestJobs.as_view()),
    url(r'^cancel_jobs/$', views.CancelJobs.as_view()),
    url(r'^fake_jobs/$', views.FakeJobs.as_view()),
    url(r'^clear_jobs/$', views.ClearJobs.as_view())
]
