from django.http import JsonResponse
from django.forms.models import model_to_dict
from rest_framework.views import APIView
from .tasks import get_video_candidates
from .models import Status


def get_job():
    return {
        'video_id': 312829497,
        'st_time': 25,
        'end_time': 63,
    }


class JobsAvailableView(APIView):
    def get(self, request, format=None):
        status = Status.objects.get(pk=1)
        data = {'jobs_available': 'yes' if status.jobs_available else 'no'}
        if status.jobs_available:
            data['job'] = get_job()
            status.jobs_available = False
            status.save()
        get_video_candidates.delay(15)
        return JsonResponse(data)


class StatusView(APIView):
    def get(self, request, format=None):
        status = Status.objects.get(pk=1)
        status = 'processing' if status.processing else 'idle'
        return JsonResponse({'status': status})


class RequestJobs(APIView):
    def get(self, request, format=None):
        status = Status.objects.get(pk=1)
        processing = status.processing
        locked = status.locked
        request_response = ''
        if locked and processing:
            request_response = 'Something went wrong'
        elif locked and not processing:
            request_response = 'There is a previous request'
        elif not locked and processing:
            request_response = 'Already processing'
        elif not locked and not processing:
            request_response = 'Processing started'
            try:
                status.locked = True
                status.save()
                status.processing = True
                status.locked = False
                status.save()
            except Exception as e:
                request_response = 'There was an error when starting the processing %s' % repr(e)
        data = {'status': model_to_dict(status), 'request_response': request_response}
        return JsonResponse(data)


class CancelJobs(APIView):
    def get(self, request, format=None):
        status = Status.objects.get(pk=1)
        locked = status.locked
        processing = status.processing
        cancel_response = ''
        if locked and processing:
            cancel_response = 'Something went wrong'
        elif locked and not processing:
            cancel_response = 'There is a previous request'
        elif not locked and processing:
            try:
                status.locked = True
                status.save()
                status.processing = False
                status.locked = False
                status.save()
                cancel_response = 'Processing Cancelled'
            except Exception as e:
                cancel_response = 'There was an error when cancelling the processing %s' % repr(e)
        elif not locked and not processing:
            cancel_response = ''
        data = {'status': model_to_dict(status), 'cancel_response': cancel_response}
        return JsonResponse(data)


class FakeJobs(APIView):
    def get(self, request, format=None):
        status = Status.objects.get(pk=1)
        status.jobs_available = True
        status.save()
        return JsonResponse({'status': model_to_dict(status)})


class ClearJobs(APIView):
    def get(self, request, format=None):
        status = Status.objects.get(pk=1)
        status.jobs_available = True
        status.save()
        return JsonResponse({'status': model_to_dict(status)})



