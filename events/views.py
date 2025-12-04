from django.shortcuts import render, get_object_or_404, redirect
from .models import Event

def event_list(request):
    events = Event.objects.all()
    return render(request, 'events/event_list.html', {'events': events})

def event_detail(request, pk):
    event = get_object_or_404(Event, pk=pk)
    return render(request, 'events/event_detail.html', {'event': event})

def register_event(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if event.remaining_seats() > 0:
        event.booked_seats += 1
        event.save()
    return redirect('event_detail', pk=pk)
