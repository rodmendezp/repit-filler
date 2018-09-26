from django.http import JsonResponse
from django.forms.models import model_to_dict
from rest_framework import status
from rest_framework.views import APIView, Response
from .tasks import request_jobs
from .models import Status
from .repitfiller.repit_filler import RepitFiller


def get_job():
    repit_filler = RepitFiller()
    repit_filler.init_jobs()
    if repit_filler.jobs_queue.method.message_count == 1:
        filler_status = Status.objects.get(pk=1)
        filler_status.jobs_available = False
        filler_status.save()
    elif repit_filler.jobs_queue.method.message_count == 0:
        return ''
    return repit_filler.get_job()


class JobsAvailableView(APIView):
    def get(self, request, format=None):
        filler_status = Status.objects.get(pk=1)
        data = {'jobs_available': 'yes' if filler_status.jobs_available else 'no'}
        if filler_status.jobs_available:
            data['job'] = get_job()
        return JsonResponse(data)

    def put(self, request, format=None):
        filler_status = Status.objects.get(pk=1)
        jobs_available = request.data.get('jobs_available', None)
        if jobs_available and (jobs_available == 'True' or jobs_available == 'False'):
            filler_status.jobs_available = bool(jobs_available)
            filler_status.save()
            return Response({'filler_status': model_to_dict(filler_status)})
        return Response({'error': 'request data need to be boolean'}, status=status.HTTP_400_BAD_REQUEST)


class StatusView(APIView):
    def get(self, request, format=None):
        filler_status = Status.objects.get(pk=1)
        data = {
            'status_short': 'processing' if filler_status.processing else 'idle',
            'filler_status': model_to_dict(filler_status)
        }
        return JsonResponse(data)


class RequestJobs(APIView):
    def get(self, request, format=None):
        filler_status = Status.objects.get(pk=1)
        processing = filler_status.processing
        locked = filler_status.locked
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
                filler_status.locked = True
                filler_status.save()
                request_jobs.delay()
                filler_status.processing = True
                filler_status.locked = False
                filler_status.save()
            except Exception as e:
                request_response = 'There was an error when starting the processing %s' % repr(e)
        data = {'filler_status': model_to_dict(filler_status), 'request_response': request_response}
        return JsonResponse(data)


class CancelJobs(APIView):
    def get(self, request, format=None):
        filler_status = Status.objects.get(pk=1)
        locked = filler_status.locked
        processing = filler_status.processing
        cancel_response = ''
        if locked and processing:
            cancel_response = 'Something went wrong'
        elif locked and not processing:
            cancel_response = 'There is a previous request'
        elif not locked and processing:
            try:
                filler_status.locked = True
                filler_status.save()
                filler_status.processing = False
                filler_status.locked = False
                filler_status.save()
                cancel_response = 'Processing Cancelled'
            except Exception as e:
                cancel_response = 'There was an error when cancelling the processing %s' % repr(e)
        elif not locked and not processing:
            cancel_response = ''
        data = {'filler_status': model_to_dict(filler_status), 'cancel_response': cancel_response}
        return JsonResponse(data)


class FakeJobs(APIView):
    def get(self, request, format=None):
        filler_status = Status.objects.get(pk=1)
        filler_status.jobs_available = True
        filler_status.save()
        return JsonResponse({'filler_status': model_to_dict(filler_status)})


class ClearJobs(APIView):
    def get(self, request, format=None):
        filler_status = Status.objects.get(pk=1)
        filler_status.jobs_available = True
        filler_status.save()
        return JsonResponse({'filler_status': model_to_dict(filler_status)})



