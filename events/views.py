from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import Event, Registration
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.contrib.admin.views.decorators import staff_member_required

def event_list(request):
    events = Event.objects.all()
    return render(request, 'events/event_list.html', {'events': events})

def event_detail(request, pk):
    event = get_object_or_404(Event, pk=pk)
    return render(request, 'events/event_detail.html', {'event': event})

@login_required
def register_event(request, pk):
    event = get_object_or_404(Event, pk=pk)
    tickets_requested = int(request.POST.get('tickets', 1))

    if tickets_requested < 1 or tickets_requested > 4:
        messages.error(request, "You can book between 1 and 4 tickets.")
        return redirect('event_detail', pk=pk)

    if event.remaining_seats >= tickets_requested:
        registration, created = Registration.objects.get_or_create(
            user=request.user,
            event=event,
            defaults={'tickets_booked': tickets_requested}
        )
        if not created:
            total_tickets = registration.tickets_booked + tickets_requested
            if total_tickets > 4:
                messages.warning(request, "You cannot book more than 4 tickets for this event.")
            else:
                registration.tickets_booked = total_tickets
                registration.save()
                messages.success(request, f"Booked {tickets_requested} more tickets!")
        else:
            messages.success(request, f"Successfully booked {tickets_requested} tickets!")
    else:
        messages.error(request, "Not enough seats available.")
    return redirect('event_detail', pk=pk)

@login_required
def user_dashboard(request):
    registrations = Registration.objects.filter(user=request.user).select_related('event')
    return render(request, 'events/user_dashboard.html', {'registrations': registrations})

@staff_member_required
def admin_report(request):
    registrations = Registration.objects.select_related('event', 'user')
    return render(request, 'events/admin_report.html', {'registrations': registrations})

def custom_logout(request):
    logout(request)
    return redirect('event_list')