
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User



class Claim(models.Model):
    claim_id = models.BigIntegerField(primary_key=True)
    patient_name = models.CharField(max_length=255, default='')
    billed_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)

    choices_status = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('denied', 'Denied'),
        ('under_review', 'Under Review'),
    ]
    status = models.CharField(max_length=255, choices=choices_status, default='pending')

    insurer_name = models.CharField(max_length=255, default='')
    discharge_date = models.DateField(default=timezone.now)

    def __str__(self):
        return f"Claim {self.claim_id} - {self.patient_name}"

    class Meta:
        ordering = ['-claim_id']


class ClaimDetail(models.Model):
    id = models.BigAutoField(primary_key=True)
    claim = models.ForeignKey('Claim', on_delete=models.CASCADE, related_name='details')
    cpt_code = models.CharField(max_length=255, default='')
    denial_reason = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Detail {self.id} for Claim {self.claim.claim_id}"


class ClaimFlag(models.Model):
    """User-generated flags for claims requiring review"""
    claim = models.ForeignKey(Claim, on_delete=models.CASCADE, related_name='flags')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    reason = models.CharField(max_length=255, help_text="Reason for flagging")
    created_at = models.DateTimeField(auto_now_add=True)
    resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_flags')

    def __str__(self):
        return f"Flag on Claim {self.claim.claim_id} by {self.user.username}"

    class Meta:
        ordering = ['-created_at']


class ClaimNote(models.Model):
    """User-generated notes and annotations for claims"""
    claim = models.ForeignKey(Claim, on_delete=models.CASCADE, related_name='notes')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Note on Claim {self.claim.claim_id} by {self.user.username}"

    class Meta:
        ordering = ['-created_at']