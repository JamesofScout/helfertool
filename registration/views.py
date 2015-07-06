from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, HttpResponse, Http404
from django.shortcuts import render, get_object_or_404, redirect
from django.utils.translation import ugettext as _

from io import BytesIO

from .models import Event, Job, Helper, Shift
from .forms import RegisterForm, EventForm, JobForm, ShiftForm, HelperForm, \
                   HelperDeleteForm, ShiftDeleteForm, JobDeleteForm, \
                   EventDeleteForm
from .utils import escape_filename
from .export import xlsx

def nopermission(request):
    return render(request, 'registration/admin/nopermission.html')


def superuser_or_admin(user, event_url_name=None):
    if user.is_superuser:
        return True

    try:
        event = Event.objects.get(url_name=event_url_name)
        if event.is_admin(user):
            return True
    except Event.DoesNotExist:
        pass

    return False

def get_or_404(event_url_name=None, job_pk=None, shift_pk=None,
                   helper_pk=None):

    # default values
    event, job, shift, helper = None, None, None, None

    # get all data, if needed
    if event_url_name:
        event = get_object_or_404(Event, url_name=event_url_name)
    if job_pk:
        job = get_object_or_404(Job, pk=job_pk)
    if shift_pk:
        shift = get_object_or_404(Shift, pk=shift_pk)
    if helper_pk:
        helper = get_object_or_404(Helper, pk=helper_pk)

    # sanity checks
    if event and job and job.event != event:
        raise Http404

    if job and shift and shift.job != job:
        raise Http404

    # return data
    return event, job, shift, helper


def index(request):
    events = Event.objects.all()

    # check is user is admin
    for e in events:
        e.is_admin = e.is_admin(request.user)

    # filter events, that are not active and where user is not admin
    active_events = [e for e in events if e.active]
    administered_events = [e for e in events if not  e.active and e.is_admin]

    context = {'active_events': active_events,
               'administered_events': administered_events}
    return render(request, 'registration/index.html', context)

def form(request, event_url_name):
    event = get_object_or_404(Event, url_name=event_url_name)

    # check permission
    if not event.active:
        # not logged in -> show login form
        if not request.user.is_authenticated():
            return redirect('%s?next=%s' % (settings.LOGIN_URL, request.path))
        # logged in -> check permission
        elif not event.is_admin(request.user):
            return nopermission(request)

    # handle form
    form = RegisterForm(request.POST or None, event=event)

    if form.is_valid():
        helper = form.save()
        helper.send_mail()
        return HttpResponseRedirect(reverse('registered', args=[event.url_name, helper.pk]))

    context = {'event': event,
               'form': form}
    return render(request, 'registration/form.html', context)

def registered(request, event_url_name, helper_id):
    event = get_object_or_404(Event, url_name=event_url_name)
    helper = get_object_or_404(Helper, pk=helper_id)

    context = {'event': event,
               'data': helper}
    return render(request, 'registration/registered.html', context)

@login_required
def admin(request, event_url_name=None):
    # check permission
    if not superuser_or_admin(request.user, event_url_name):
        return nopermission(request)

    # get event
    event = None
    if event_url_name:
        event = get_object_or_404(Event, url_name=event_url_name)

    # response
    context = {'event': event}
    return render(request, 'registration/admin/index.html', context)


@login_required
def edit_event(request, event_url_name=None):
    # check permission
    if not superuser_or_admin(request.user, event_url_name):
        return nopermission(request)

    # get event
    event = None
    if event_url_name:
        event = get_object_or_404(Event, url_name=event_url_name)

    # handle form
    form = EventForm(request.POST or None, instance=event)

    if form.is_valid():
        helper = form.save()

        # redirect to this page, so reload does not send the form data again
        # if the event was created, this redirects to the event settings
        #if event_url_name:  # edit of existing event
        #    new_url_name = event.url_name
        #else:  # new event created
        #    new_url_name = form['url_name'].value()
        return HttpResponseRedirect(reverse('edit_event', args=[form['url_name'].value()]))

    # get event without possible invalid modifications from form
    saved_event = None
    if event_url_name:
        saved_event = get_object_or_404(Event, url_name=event_url_name)

    # render page
    context = {'event': saved_event,
               'form': form}
    return render(request, 'registration/admin/edit_event.html', context)

@login_required
def jobs_and_shifts(request, event_url_name):
    event = get_object_or_404(Event, url_name=event_url_name)

    # check permission
    if not event.is_admin(request.user):
        return nopermission(request)

    # list all jobs and shifts
    context = {'event': event}
    return render(request, 'registration/admin/jobs_and_shifts.html', context)


@login_required
def edit_job(request, event_url_name, job_pk=None):
    event = get_object_or_404(Event, url_name=event_url_name)

    # check permission
    if not event.is_admin(request.user):
        return nopermission(request)

    # get job, if available
    job = None
    if job_pk:
        job = get_object_or_404(Job, pk=job_pk)

    # form
    form = JobForm(request.POST or None, instance=job, event=event)

    if form.is_valid():
        job = form.save()
        return HttpResponseRedirect(reverse('jobs_and_shifts', args=[event_url_name]))

    # render page
    context = {'event': event,
               'job': job,
               'form': form}
    return render(request, 'registration/admin/edit_job.html', context)

@login_required
def edit_shift(request, event_url_name, job_pk, shift_pk=None):
    event, job, shift, helper = get_or_404(event_url_name, job_pk, shift_pk)

    # check permission
    if not event.is_admin(request.user):
        return nopermission(request)

    # form
    form = ShiftForm(request.POST or None, instance=shift, job=job)

    if form.is_valid():
        job = form.save()
        return HttpResponseRedirect(reverse('jobs_and_shifts', args=[event_url_name]))

    # render page
    context = {'event': job.event,
               'job': job,
               'shift': shift,
               'form': form}
    return render(request, 'registration/admin/edit_shift.html', context)

@login_required
def edit_helper(request, event_url_name, helper_pk):
    event, job, shift, helper = get_or_404(event_url_name, helper_pk=helper_pk)

    # check permission
    if not event.is_admin(request.user):
        return nopermission(request)

    # form
    form = HelperForm(request.POST or None, instance=helper)

    if form.is_valid():
        form.save()
        return HttpResponseRedirect(reverse('helpers', args=[event_url_name]))

    # render page
    context = {'event': event,
               'helper': helper,
               'form': form}
    return render(request, 'registration/admin/edit_helper.html', context)

@login_required
def delete_helper(request, event_url_name, helper_pk, job_pk):
    event, job, shift, helper = get_or_404(event_url_name,
                                               job_pk=job_pk,
                                               helper_pk=helper_pk)
    # check permission
    if not event.is_admin(request.user):
        return nopermission(request)

    # form
    form = HelperDeleteForm(request.POST or None, instance=helper)

    if form.is_valid():
        # delete shifts or complete helpers
        form.delete()
        messages.success(request, _("Helper deleted: %(name)s") % {'name': helper.full_name})

        # redirect to shift
        return HttpResponseRedirect(reverse('jobhelpers', args=[event_url_name, job.pk]))

    # render page
    context = {'event': event,
               'helper': helper,
               'job': job,
               'form': form}
    return render(request, 'registration/admin/delete_helper.html', context)

@login_required
def delete_shift(request, event_url_name, job_pk, shift_pk):
    event, job, shift, helper = get_or_404(event_url_name, job_pk, shift_pk)

    # check permission
    if not event.is_admin(request.user):
        return nopermission(request)

    # form
    form = ShiftDeleteForm(request.POST or None, instance=shift)

    if form.is_valid():
        form.delete()
        messages.success(request, _("Shift deleted"))

        # redirect to shift
        return HttpResponseRedirect(reverse('jobs_and_shifts', args=[event_url_name]))

    # render page
    context = {'event': event,
               'shift': shift,
               'job': job,
               'form': form}
    return render(request, 'registration/admin/delete_shift.html', context)

@login_required
def delete_job(request, event_url_name, job_pk):
    event, job, shift, helper = get_or_404(event_url_name, job_pk)

    # check permission
    if not event.is_admin(request.user):
        return nopermission(request)

    # form
    form = JobDeleteForm(request.POST or None, instance=job)

    if form.is_valid():
        form.delete()
        messages.success(request, _("Job deleted: %(name)s") % {'name': job.name})


        # redirect to shift
        return HttpResponseRedirect(reverse('jobs_and_shifts', args=[event_url_name]))

    # check, if there are helpers registered
    helpers_registered = False
    for shift in job.shift_set.all():
        if shift.helper_set.count() > 0:
            helpers_registered = True
            break

    # render page
    context = {'event': event,
               'job': job,
               'helpers_registered': helpers_registered,
               'form': form}
    return render(request, 'registration/admin/delete_job.html', context)

@login_required
def delete_event(request, event_url_name):
    event = get_object_or_404(Event, url_name=event_url_name)

    # check permission
    if not event.is_admin(request.user):
        return nopermission(request)

    # form
    form = EventDeleteForm(request.POST or None, instance=event)

    if form.is_valid():
        form.delete()
        messages.success(request, _("Event deleted: %(name)s") % {'name': event.name})

        # redirect to shift
        return HttpResponseRedirect(reverse('index'))

    # render page
    context = {'event': event,
               'form': form}
    return render(request, 'registration/admin/delete_event.html', context)

@login_required
def helpers(request, event_url_name, job_pk=None):
    event = get_object_or_404(Event, url_name=event_url_name)

    # check permission
    if not event.is_admin(request.user):
        return nopermission(request)

    # helpers of one job
    if job_pk:
        job = get_object_or_404(Job, pk=job_pk)
        context = {'event': event, 'job': job}
        return render(request, 'registration/admin/helpers_for_job.html', context)

    # overview over jobs
    context = {'event': event}
    return render(request, 'registration/admin/helpers.html', context)

@login_required
def excel(request, event_url_name, job_pk=None):
    event = get_object_or_404(Event, url_name=event_url_name)

    # check permission
    if not event.is_admin(request.user):
        return nopermission(request)

    # list of jobs for export
    if job_pk:
        job = get_object_or_404(Job, pk=job_pk)
        jobs = [job, ]
        filename = "%s - %s" % (event.name, job.name)
    else:
        jobs = event.job_set.all()
        filename = event.name

    # start http response
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="%s.xlsx"' % escape_filename(filename)

    # create buffer
    buffer = BytesIO()

    xlsx(buffer, event, jobs)

    # close buffer, send file
    data = buffer.getvalue()
    buffer.close()
    response.write(data)

    return response
