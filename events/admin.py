from django.contrib import admin
from .models import Event, Registration

class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'venue', 'date_time', 'total_seats', 'remaining_seats', 'booked_seats')

    def booked_seats(self, obj):
        return obj.booked_seats()
    booked_seats.short_description = "Booked Seats"

class RegistrationAdmin(admin.ModelAdmin):
    list_display = ('user', 'event', 'tickets_booked', 'tracking_code', 'status', 'registered_at')
    list_filter = ('event', 'user')
    search_fields = ('user__username', 'event__title')

admin.site.register(Event, EventAdmin)
admin.site.register(Registration, RegistrationAdmin)
