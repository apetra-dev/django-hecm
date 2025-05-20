from django.db import models
from .config import HECMConfig

class PLFTable(models.Model):
    """Principal Limit Factor table entries"""
    config = models.ForeignKey(
        HECMConfig,
        on_delete=models.CASCADE,
        related_name="plf_entries"
    )

    age = models.IntegerField(help_text="Age of youngest borrower")
    interest_rate = models.DecimalField(
        max_digits=5,
        decimal_places=3,
        help_text="Expected interest rate"
    )
    factor = models.DecimalField(
        max_digits=6,
        decimal_places=5,
        help_text="Principal Limit Factor"
    )

    class Meta:
        unique_together = ["config", "age", "interest_rate"]

