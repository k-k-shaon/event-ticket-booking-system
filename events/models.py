from django.db import models

# Create your models here.

class Event(models.Model):
    title = models.CharField(max_length=200)
    venue = models.CharField(max_length=200)
    date_time = models.DateTimeField()
    description = models.TextField()
    total_seats = models.PositiveIntegerField()
    booked_seats = models.PositiveIntegerField(default=0)

    def remaining_seats(self):
        return self.total_seats - self.booked_seats

    def __str__(self):
        return self.title
