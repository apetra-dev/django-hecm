from django.db import models
from .config import HECMConfig

class HECMInput(models.Model):
    """Model to store HECM input parameters"""
    created_at = models.DateTimeField(auto_now_add=True)
    home_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Value of the home in dollars"
    )

    age = models.IntegerField(
        help_text="Age of the youngest borrower or eligible non-borrowing spouse"
    )
    interest_rate = models.DecimalField(
        max_digits=5,
        decimal_places=3,
        help_text="Expected interest rate (annual)"
    )
    existing_mortgage = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Amount needed to pay off existing mortgage"
    )
    def clean(self):
        """Validate inputs"""
        config = HECMConfig.get_current()
        if self.age < config.min_age:
            raise ValueError(f"Borrower must be at least {config.min_age} years old to qualify for HECM")
        if self.home_value <= 0:
            raise ValueError("Home value must be positive")
        if self.interest_rate <= 0:
            raise ValueError("Interest rate must be positive")
        if self.existing_mortgage < 0:
            raise ValueError("Existing mortgage cannot be negative")
