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

def login_success(request):
    messages.success(request, f"Welcome back, {request.user.username}!")
    return redirect('event_list')

@login_required
def register_event(request, pk):
    event = get_object_or_404(Event, pk=pk)
    tickets_requested = int(request.POST.get('tickets', 1))

    if tickets_requested < 1 or tickets_requested > 4:
        messages.error(request, "You can book between 1 and 4 tickets.")
        return redirect('event_detail', pk=pk)

    registration = Registration.objects.filter(user=request.user, event=event).first()

    if registration:
        # User already has a booking
        total_tickets = registration.tickets_booked + tickets_requested
        if total_tickets > 4:
            messages.warning(request, "You already booked tickets. Max 4 per user.")
        else:
            if event.remaining_seats >= tickets_requested:
                registration.tickets_booked = total_tickets
                registration.save()
                messages.success(request, f"Added {tickets_requested} more tickets. Total: {total_tickets}")
            else:
                messages.error(request, "Not enough seats available.")
    else:
        # First time booking
        if event.remaining_seats >= tickets_requested:
            Registration.objects.create(
                user=request.user,
                event=event,
                tickets_booked=tickets_requested
            )
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
    messages.success(request, "You have been logged out successfully.")
    return redirect('event_list')