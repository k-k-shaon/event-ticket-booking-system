from django.db import models
from django.contrib.auth.models import User
import uuid

class Event(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    venue = models.CharField(max_length=200)
    date_time = models.DateTimeField()
    total_seats = models.IntegerField()
    ticket_price = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    def booked_seats(self):
        return sum(r.tickets_booked for r in Registration.objects.filter(event=self))

    @property
    def remaining_seats(self):
        return self.total_seats - self.booked_seats()

    def __str__(self):
        return self.title
# class Registration(models.Model):
#     user = models.ForeignKey(User, on_delete=models.CASCADE)
#     event = models.ForeignKey(Event, on_delete=models.CASCADE)
#     tickets_booked = models.PositiveIntegerField(default=1)
#     registered_at = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         unique_together = ('user', 'event')

class Registration(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('complete', 'Complete'),
        ('rejected', 'Rejected'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    student_id = models.CharField(max_length=20, null=True, blank=True)
    phone_number = models.CharField(max_length=15, null=True, blank=True)
    transaction_id = models.CharField(max_length=50, unique=True)
    payment_method = models.CharField(max_length=20, choices=[('bkash','bKash'),('nagad','Nagad'),('rocket','Rocket')])
    tickets_booked = models.PositiveIntegerField(default=1)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    registered_at = models.DateTimeField(auto_now_add=True)
    tracking_code = models.CharField(max_length=50, unique=True, blank=True, null=True)


    def __str__(self):
        return f"{self.user.username} - {self.event.title} ({self.status})"
    
    def save(self, *args, **kwargs):
        if not self.tracking_code:
            self.tracking_code = f"TKT-{self.event.id}-{uuid.uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)


class PaymentMethod(models.Model):
    METHOD_CHOICES = [
        ('bkash', 'bKash'),
        ('nagad', 'Nagad'),
        ('rocket', 'Rocket'),
    ]

    method = models.CharField(max_length=20, choices=METHOD_CHOICES, unique=True)
    number = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.get_method_display()} - {self.number}"
