from django.db import models
from decimal import Decimal


class HECMConfig(models.Model):
    """Configuration settings for HECM calculations that may change over time"""
    effective_date = models.DateField(help_text="Date these settings take effect")
    fha_lending_limit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Maximum FHA lending limit"
    )
    min_age = models.IntegerField(
        default=62,
        help_text="Minimum age to qualify for HECM"
    )
    mip_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=0.02,
        help_text="Mortgage Insurance Premium rate"
    )
    origination_fee_min = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=2500,
        help_text="Minimum origination fee"
    )
    origination_fee_cap = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=6000,
        help_text="Maximum origination fee"
    )
    first_tier_limit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=200000,
        help_text="Limit for first tier origination fee calculation"
    )
    first_tier_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=0.02,
        help_text="Rate for first tier origination fee calculation"
    )
    second_tier_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=0.01,
        help_text="Rate for second tier origination fee calculation"
    )

    class Meta:
        get_latest_by = "effective_date"

    @classmethod
    def get_current(cls):
        """Get the most recent configuration"""
        try:
            return cls.objects.latest()
        except cls.DoesNotExist:
            # Create default config if none exists
            return cls.objects.create(
                effective_date="2025-01-01",
                fha_lending_limit=Decimal('1089300'),
                min_age=62,
                mip_rate=Decimal('0.02'),
                origination_fee_min=Decimal('2500'),
                origination_fee_cap=Decimal('6000'),
                first_tier_limit=Decimal('200000'),
                first_tier_rate=Decimal('0.02'),
                second_tier_rate=Decimal('0.01')
            )
