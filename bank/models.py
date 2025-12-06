from django.db import models
from django.conf import settings

class Account(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    account_number = models.CharField(max_length=32, unique=True)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.account_number} ({self.user.username})"


class Transaction(models.Model):
    # short codes for type, human readable in admin/templates via get_txn_type_display()
    TXN_TYPES = (
        ('CR', 'Credit'),
        ('DR', 'Debit'),
        ('TR', 'Transfer'),
        ('DP', 'Deposit'),
        ('WD', 'Withdraw'),
        ('RC', 'Received'),
    )

    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='transactions')
    txn_type = models.CharField(max_length=2, choices=TXN_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    timestamp = models.DateTimeField(auto_now_add=True)
    description = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['-timestamp']  # newest first

    def __str__(self):
        return f"{self.get_txn_type_display()} {self.amount} on {self.timestamp:%Y-%m-%d}"
