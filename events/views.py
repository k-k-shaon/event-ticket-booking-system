from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Count, Q
from .models import Event, Registration, PaymentMethod
from .forms import EventForm, PaymentMethodForm


# -------------------- Public/User Views --------------------

def event_list(request):
    events = Event.objects.all()
    return render(request, 'events/event_list.html', {'events': events})

def event_detail(request, pk):
    event = get_object_or_404(Event, pk=pk)
    event_past = event.date_time < timezone.now()

    # If user is not logged in, show message but allow page view
    if not request.user.is_authenticated:
        messages.info(request, "Login to book tickets.")
        return render(request, 'events/event_detail.html', {'event': event, 'event_past': event_past})

    # Superuser cannot book
    if request.user.is_superuser:
        messages.info(request, "Superusers cannot book tickets.")
        return render(request, 'events/event_detail.html', {'event': event, 'event_past': event_past})

    if request.method == 'POST':
        if event_past:
            messages.error(request, "Registration is closed for this event.")
            return redirect('event_detail', pk=pk)

        tickets_requested = int(request.POST.get('tickets', 1))
        total_tickets = sum(r.tickets_booked for r in Registration.objects.filter(user=request.user, event=event))

        if total_tickets + tickets_requested > 4:
            messages.error(request, "Maximum ticket limit (4) exceeded.")
            return render(request, 'events/event_detail.html', {'event': event, 'event_past': event_past})

        return redirect(f"/event/{event.id}/payment/?tickets={tickets_requested}")

    return render(request, 'events/event_detail.html', {'event': event, 'event_past': event_past})

@login_required(login_url='/')
def register_event(request, pk):
    event = get_object_or_404(Event, pk=pk)

    # Superuser cannot register
    if request.user.is_superuser:
        messages.warning(request, "Superusers cannot register for events.")
        return redirect('event_detail', pk=pk)

    if event.date_time < timezone.now():
        messages.error(request, "Registration is closed for this event.")
        return redirect('event_detail', pk=pk)

    tickets_requested = int(request.POST.get('tickets', 1))
    if tickets_requested < 1 or tickets_requested > 4:
        messages.error(request, "You can book between 1 and 4 tickets.")
        return redirect('event_detail', pk=pk)

    registration = Registration.objects.filter(user=request.user, event=event).first()

    if registration:
        total_tickets = registration.tickets_booked + tickets_requested
        if total_tickets > 4:
            messages.warning(request, "Already booked tickets. Max 4 per user.")
        else:
            if event.remaining_seats >= tickets_requested:
                registration.tickets_booked = total_tickets
                registration.save()
                messages.success(request, f"Added {tickets_requested} more tickets. Total: {total_tickets}")
            else:
                messages.error(request, "Not enough seats available.")
    else:
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

@login_required(login_url='/')
def payment_page(request, pk):
    event = get_object_or_404(Event, pk=pk)

    # Superuser cannot pay
    if request.user.is_superuser:
        messages.warning(request, "Superusers cannot pay for events.")
        return redirect('event_detail', pk=pk)

    if event.date_time < timezone.now():
        messages.error(request, "Payment is closed. This event is over.")
        return redirect('event_detail', pk=pk)

    tickets_requested = int(request.GET.get('tickets', 1))
    total_price = tickets_requested * event.ticket_price

    if request.method == 'POST':
        name = request.POST.get('name')
        student_id = request.POST.get('student_id')
        phone_number = request.POST.get('phone_number')
        transaction_id = request.POST.get('transaction_id')
        payment_method = request.POST.get('payment_method')

        total_tickets = sum(r.tickets_booked for r in Registration.objects.filter(user=request.user, event=event))
        if total_tickets + tickets_requested > 4:
            messages.warning(request, "Maximum number of tickets (4) exceeded.")
            return redirect('user_dashboard')

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
    
    payment_methods = PaymentMethod.objects.filter(is_active=True)

    return render(request, 'events/payment_page.html', {
        'event': event,
        'tickets_requested': tickets_requested,
        'total_price': total_price,
        'payment_methods': payment_methods,

    })

@login_required(login_url='/')
def ticket_view(request, tracking_code):
    reg = get_object_or_404(
        Registration,
        tracking_code=tracking_code,
        user=request.user,
        status='complete'
    )

    return render(request, 'tickets/boarding_pass.html', {
        'reg': reg,
        'event': reg.event,
    })

# -------------------- Admin Views --------------------

def admin_access_login(request):
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect('admin_dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user and user.is_superuser:
            login(request, user)
            return redirect('admin_dashboard')
        messages.error(request, 'Invalid credentials or not a superuser.')

    return render(request, 'admin_access/login.html')

def admin_dashboard(request):
    if not request.user.is_authenticated or not request.user.is_superuser:
        messages.error(request, "You do not have access to this page.")
        return redirect('event_list')

    events = Event.objects.annotate(
        approved_count=Count('registration', filter=Q(registration__status='complete'))
    ).order_by('-date_time')
    pending_regs = Registration.objects.filter(status='pending').select_related('event', 'user')
    approved_regs = Registration.objects.filter(status='complete').select_related('event', 'user')
    return render(request, 'admin_access/dashboard.html', {
        'events': events,
        'pending_regs': pending_regs,
        'approved_regs': approved_regs,
    })

def admin_create_event(request):
    if not request.user.is_authenticated or not request.user.is_superuser:
        messages.error(request, "You do not have access to create events.")
        return redirect('event_list')

    if request.method == 'POST':
        form = EventForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Event created successfully.')
            return redirect('admin_dashboard')
        messages.error(request, 'Please fix the errors below.')
    else:
        form = EventForm()
    return render(request, 'admin_access/event_form.html', {'form': form})

def admin_approve_registration(request, reg_id):
    if not request.user.is_authenticated or not request.user.is_superuser:
        messages.error(request, "You do not have permission.")
        return redirect('event_list')

    reg = get_object_or_404(Registration, id=reg_id)
    reg.status = 'complete'
    reg.save()
    messages.success(request, f"Approved registration for {reg.user.username} ({reg.event.title})")
    return redirect('admin_dashboard')

def admin_reject_registration(request, reg_id):
    if not request.user.is_authenticated or not request.user.is_superuser:
        messages.error(request, "You do not have permission.")
        return redirect('event_list')

    reg = get_object_or_404(Registration, id=reg_id)
    reg.delete()
    messages.warning(request, f"Rejected registration for {reg.user.username} ({reg.event.title})")
    return redirect('admin_dashboard')

def admin_access_logout(request):
    logout(request)
    return redirect('admin_access_login')

@login_required(login_url='/')
def login_success(request):
    messages.success(request, f"Welcome back, {request.user.username}!")
    return redirect('event_list')

@login_required(login_url='/')
def custom_logout(request):
    logout(request)
    messages.success(request, "You have successfully logged out.")
    return redirect('event_list')

@login_required(login_url='/')
def user_dashboard(request):
    if request.user.is_superuser:
        return redirect('admin_dashboard')

    registrations = Registration.objects.filter(user=request.user).select_related('event')
    return render(request, 'events/user_dashboard.html', {'registrations': registrations})

def admin_edit_event(request, pk):
    if not request.user.is_authenticated or not request.user.is_superuser:
        messages.error(request, "You do not have permission.")
        return redirect('event_list')

    event = get_object_or_404(Event, pk=pk)

    if request.method == 'POST':
        form = EventForm(request.POST, instance=event)
        if form.is_valid():
            form.save()
            messages.success(request, "Event updated successfully.")
            return redirect('admin_dashboard')
    else:
        form = EventForm(instance=event)

    return render(request, 'admin_access/event_form.html', {
        'form': form,
        'edit_mode': True
    })

def admin_delete_event(request, pk):
    if not request.user.is_authenticated or not request.user.is_superuser:
        messages.error(request, "You do not have permission.")
        return redirect('event_list')

    event = get_object_or_404(Event, pk=pk)
    event.delete()
    messages.warning(request, "Event deleted successfully.")
    return redirect('admin_dashboard')

@login_required(login_url='/')
def manage_payment_methods(request):
    if not request.user.is_superuser:
        messages.error(request, "You are not authorized.")
        return redirect('event_list')

    methods = PaymentMethod.objects.all()

    if request.method == 'POST':
        form = PaymentMethodForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Payment method saved.")
            return redirect('manage_payment_methods')
    else:
        form = PaymentMethodForm()

    return render(request, 'admin_access/payment_methods.html', {
        'methods': methods,
        'form': form
    })

@login_required
def edit_payment_method(request, pk):
    if not request.user.is_superuser:
        messages.error(request, "You do not have permission.")
        return redirect('event_list')

    method = get_object_or_404(PaymentMethod, pk=pk)

    if request.method == 'POST':
        form = PaymentMethodForm(request.POST, instance=method)
        if form.is_valid():
            form.save()
            messages.success(request, "Payment Method updated successfully.")
            return redirect('manage_payment_methods')  # back to list
    else:
        form = PaymentMethodForm(instance=method)

    return render(request, 'admin_access/payment_methods.html', {
        'form': form,
        'edit_mode': True
    })