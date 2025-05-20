from django.db import models
from decimal import Decimal
from django.core.exceptions import ValidationError
from .config import HECMConfig


class HECMInput(models.Model):
    """Input parameters for HECM calculations"""
    age = models.IntegerField(help_text="Age of youngest borrower")
    home_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Appraised home value"
    )
    margin = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=Decimal('2.00'),  # Default margin of 2%
        help_text="Lender's margin (percentage)"
    )
    interest_rate = models.DecimalField(
        max_digits=5,
        decimal_places=3,
        help_text="Expected interest rate (index + margin)"
    )
    existing_mortgage = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Amount of existing mortgage to be paid off"
    )

    def clean(self):
        """Validate inputs"""
        config = HECMConfig.get_current()
        if self.age < config.min_age:
            raise ValidationError(f"Borrower must be at least {config.min_age} years old to qualify for HECM")
        if self.home_value <= 0:
            raise ValidationError("Home value must be positive")
        if self.interest_rate <= 0:
            raise ValidationError("Interest rate must be positive")
        if self.existing_mortgage < 0:
            raise ValidationError("Existing mortgage cannot be negative")
        if self.margin <= 0:
            raise ValidationError("Margin must be positive")

    def __str__(self):
        return f"HECM Input for {self.age} year old, ${self.home_value}"

