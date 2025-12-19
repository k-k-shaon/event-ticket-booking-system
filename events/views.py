from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.template.loader import render_to_string
from django.http import HttpResponse
from django.utils import timezone
from django.db.models import Count, Q
from .models import Event, Registration
from .forms import EventForm
import datetime
import uuid

# For PNG ticket
import qrcode
from io import BytesIO

# Helper decorator: only superusers allowed
superuser_required = user_passes_test(lambda u: u.is_superuser)

# -------------------- Public/User Views --------------------

def event_list(request):
    events = Event.objects.all()
    return render(request, 'events/event_list.html', {'events': events})


def event_detail(request, pk):
    event = get_object_or_404(Event, pk=pk)
    event_past = event.date_time < timezone.now()  # check if event date passed

    # If user is not logged in, just show alert
    if not request.user.is_authenticated:
        messages.error(request, "You must login to book tickets.")
        return render(request, 'events/event_detail.html', {'event': event, 'event_past': event_past})

    if request.method == 'POST':
        if event_past:
            messages.error(request, "Registration is closed for this event.")
            return redirect('event_detail', pk=pk)

        tickets_requested = int(request.POST.get('tickets', 1))
        total_tickets = sum(r.tickets_booked for r in Registration.objects.filter(user=request.user, event=event))

        if total_tickets + tickets_requested > 4:
            messages.error(request, "Maximum ticket limit (4) exceeded. You cannot book more.")
            return render(request, 'events/event_detail.html', {'event': event, 'event_past': event_past})

        return redirect(f"/event/{event.id}/payment/?tickets={tickets_requested}")

    return render(request, 'events/event_detail.html', {'event': event, 'event_past': event_past})


@login_required
def register_event(request, pk):
    event = get_object_or_404(Event, pk=pk)

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
            messages.warning(request, "You already booked tickets. Max 4 per user.")
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


@login_required
def payment_page(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if event.date_time < timezone.now():
        messages.error(request, "Payment is closed. This event is over.")
        return redirect('event_detail', pk=pk)

    tickets_requested = int(request.GET.get('tickets', 1))
    total_price = tickets_requested * event.ticket_price

    if request.method == 'POST':
        name = request.POST.get('name')
        student_id = request.POST.get('student_id')
        phone_number = request.POST.get('phone_number')
        transaction_id = str(uuid.uuid4())[:8]  # auto-generate unique transaction id
        payment_method = request.POST.get('payment_method')

        total_tickets = sum(r.tickets_booked for r in Registration.objects.filter(user=request.user, event=event))

        if total_tickets + tickets_requested > 4:
            messages.warning(request, "Maximum number of tickets (4) exceeded. You cannot book more.")
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

    return render(request, 'events/payment_page.html', {
        'event': event,
        'tickets_requested': tickets_requested,
        'total_price': total_price
    })


@login_required
def download_ticket(request, reg_id):
    reg = get_object_or_404(Registration, id=reg_id, user=request.user)
    if reg.status != 'complete':
        return HttpResponse("Ticket not available. Registration not approved.", status=403)

    # Unique tracking code
    tracking_code = f"TKT-{reg.id}-{reg.event.id}-{uuid.uuid4().hex[:6].upper()}"

    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(tracking_code)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    # Convert to PNG and send as response
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    response = HttpResponse(buffer, content_type="image/png")
    filename = f"ticket_{reg.id}.png"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    return response


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


@superuser_required
def admin_dashboard(request):
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


@superuser_required
def admin_create_event(request):
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


@superuser_required
def admin_approve_registration(request, reg_id):
    reg = get_object_or_404(Registration, id=reg_id)
    reg.status = 'complete'
    reg.save()
    messages.success(request, f"Approved registration for {reg.user.username} ({reg.event.title})")
    return redirect('admin_dashboard')


@superuser_required
def admin_reject_registration(request, reg_id):
    reg = get_object_or_404(Registration, id=reg_id)
    reg.delete()
    messages.warning(request, f"Rejected registration for {reg.user.username} ({reg.event.title})")
    return redirect('admin_dashboard')


def admin_access_logout(request):
    logout(request)
    return redirect('admin_access_login')


@login_required
def login_success(request):
    messages.success(request, f"Welcome back, {request.user.username}!")
    return redirect('event_list')

@login_required
def custom_logout(request):
    logout(request)
    messages.success(request, "You have successfully logged out.")
    return redirect('event_list')

@login_required
def user_dashboard(request):
    registrations = Registration.objects.filter(user=request.user).select_related('event')
    return render(request, 'events/user_dashboard.html', {'registrations': registrations})
