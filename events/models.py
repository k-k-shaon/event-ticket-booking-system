from django.db import models
from django.contrib.auth.models import User

class Event(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    venue = models.CharField(max_length=200)
    date_time = models.DateTimeField()
    total_seats = models.IntegerField()

    def booked_seats(self):
        return sum(r.tickets_booked for r in Registration.objects.filter(event=self))

    @property
    def remaining_seats(self):
        return self.total_seats - self.booked_seats()

class Registration(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    tickets_booked = models.PositiveIntegerField(default=1)
    registered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'event')
