from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid

# PROFILE MODEL
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=15, blank=True, null=True)
    place = models.CharField(max_length=100, blank=True, null=True)
    credits = models.IntegerField(default=0)

    def __str__(self):
        return self.user.email

# SKILL MODEL
class Skill(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

# USER SKILL MODEL

class UserSkill(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE)
    is_offering = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.email} - {self.skill.name}"

# SWAP REQUEST MODEL

class SwapRequest(models.Model):

    STATUS_CHOICES = (
        ("Pending", "Pending"),
        ("Accepted", "Accepted"),
        ("Completed", "Completed"),
        ("Rejected", "Rejected"),
    )

    requester = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="sent_requests"
    )

    provider = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="received_requests"
    )

    skill = models.ForeignKey(Skill, on_delete=models.CASCADE)
    duration = models.IntegerField(default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Pending")
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.requester.email} → {self.provider.email} ({self.status})"
# MESSAGE MODEL (CHAT)
class Message(models.Model):
    swap = models.ForeignKey(
        SwapRequest,
        on_delete=models.CASCADE,
        related_name="messages"
    )
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sender.email} - {self.swap.id}"
# PAYMENT MODEL
class Payment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.IntegerField()

    transaction_id = models.CharField(
        max_length=100,
        default=uuid.uuid4,
        editable=False
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - ₹{self.amount}"

# WITHDRAW REQUEST MODEL
class WithdrawRequest(models.Model):

    STATUS_CHOICES = (
        ("Pending", "Pending"),
        ("Approved", "Approved"),
        ("Rejected", "Rejected"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.IntegerField()
    upi_id = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Pending")
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):

        # Deduct credits only when approving first time
        if self.pk:
            old = WithdrawRequest.objects.get(pk=self.pk)

            if old.status != "Approved" and self.status == "Approved":
                profile = self.user.profile

                if profile.credits >= self.amount:
                    profile.credits -= self.amount
                    profile.save()

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.email} - {self.amount}"