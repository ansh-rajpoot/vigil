from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    ROLE_CHOICES = (
        ('TOURIST', 'Tourist'),
        ('AUTHORITY', 'Law Enforcement / Authority Officer'),
        ('OPERATOR', 'Authority C2 Operator'),
        ('RESPONDER', 'Emergency Field Responder'),
        ('ADMIN', 'Tourism Administrator'),
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='TOURIST')
    phone_number = models.CharField(max_length=20, blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    badge_number = models.CharField(max_length=50, blank=True, null=True, help_text="Official badge / ID for Authority/Responder")
    agency_name = models.CharField(max_length=150, blank=True, null=True, help_text="e.g. Goa Police, Tourism Task Force, 108 EMS")
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def is_tourist(self):
        return self.role == 'TOURIST'

    @property
    def is_authority(self):
        return self.role in ['AUTHORITY', 'OPERATOR', 'RESPONDER', 'ADMIN']

    @property
    def is_operator(self):
        return self.role in ['AUTHORITY', 'OPERATOR', 'ADMIN']

    @property
    def is_responder(self):
        return self.role == 'RESPONDER'

    @property
    def is_tourism_admin(self):
        return self.role == 'ADMIN' or self.is_superuser or self.is_staff

    def get_role_badge_class(self):
        if self.is_tourism_admin:
            return 'badge-critical'
        elif self.is_authority:
            return 'badge-warning'
        return 'badge-safe'

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


class EmergencyContact(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='emergency_contacts')
    name = models.CharField(max_length=100)
    relationship = models.CharField(max_length=50, help_text="e.g. Spouse, Parent, Sibling, Friend")
    phone_number = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_primary', 'name']

    def __str__(self):
        return f"{self.name} ({self.relationship}) - {self.phone_number}"
