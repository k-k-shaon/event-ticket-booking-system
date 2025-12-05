from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import Event, Registration
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.contrib.admin.views.decorators import staff_member_required

def event_list(request):
    events = Event.objects.all()
    return render(request, 'events/event_list.html', {'events': events})

@login_required
def event_detail(request, pk):
    event = get_object_or_404(Event, pk=pk)

    if request.method == 'POST':
        tickets_requested = int(request.POST.get('tickets', 1))

        # Count how many tickets this user already booked for this event
        total_tickets = sum(r.tickets_booked for r in Registration.objects.filter(user=request.user, event=event))

        if total_tickets + tickets_requested > 4:
            # Stay on the same page and show error
            messages.error(request, "Maximum ticket limit (4) exceeded. You cannot book more.")
            return render(request, 'events/event_detail.html', {'event': event})

        # ✅ If within limit, go to payment page
        return redirect(f"/event/{event.id}/payment/?tickets={tickets_requested}")

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
    pending_regs = Registration.objects.filter(status='pending')
    events = Event.objects.all()
    return render(request, 'events/admin_report.html', {
        'pending_regs': pending_regs,
        'events': events,
    })


def custom_logout(request):
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('event_list')

@login_required
def payment_page(request, pk):
    event = get_object_or_404(Event, pk=pk)
    tickets_requested = int(request.GET.get('tickets', 1))  # from query string
    total_price = tickets_requested * event.ticket_price

    # Enforce ticket limit (1–4 per submission, not cumulative)
    if tickets_requested < 1 or tickets_requested > 4:
        messages.error(request, "You can book between 1 and 4 tickets only per submission.")
        return redirect('event_detail', pk=pk)

    if request.method == 'POST':
        name = request.POST.get('name')
        student_id = request.POST.get('student_id')
        phone_number = request.POST.get('phone_number')
        transaction_id = request.POST.get('transaction_id')
        payment_method = request.POST.get('payment_method')

        # Check if this user already has registrations for this event
        total_tickets = sum(r.tickets_booked for r in Registration.objects.filter(user=request.user, event=event))

        if total_tickets + tickets_requested > 4:
            messages.warning(request, "Maximum number of tickets (4) exceeded. You cannot book more.")
            return redirect('user_dashboard')

        # ✅ Create a NEW row for every submission (no merging)
        Registration.objects.create(
            user=request.user,
            event=event,
            name=name,
            student_id=student_id,
            phone_number=phone_number,
            transaction_id=transaction_id,
            payment_method=payment_method,
            tickets_booked=tickets_requested,
            total_price=total_price,
            status='pending'
        )
        messages.info(request, f"Submitted {tickets_requested} tickets. Awaiting admin approval.")
        return redirect('user_dashboard')

    return render(request, 'events/payment_page.html', {
        'event': event,
        'tickets_requested': tickets_requested,
        'total_price': total_price
    })




@staff_member_required
def approve_registration(request, reg_id):
    reg = get_object_or_404(Registration, id=reg_id)
    reg.status = 'complete'
    reg.save()
    messages.success(request, f"Approved registration for {reg.user.username} ({reg.event.title})")
    return redirect('admin_report')

@staff_member_required
def reject_registration(request, reg_id):
    reg = get_object_or_404(Registration, id=reg_id)
    reg.status = 'pending'  # or you can add a 'rejected' status if you want
    reg.delete()            # simplest: delete the record
    messages.warning(request, f"Rejected registration for {reg.user.username} ({reg.event.title})")
    return redirect('admin_report')