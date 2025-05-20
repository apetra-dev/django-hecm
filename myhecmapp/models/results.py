from django.db import models
from .config import HECMConfig
from .inputs import HECMInput

class HECMResult(models.Model):
    """Model to store HECM calculation results"""
    input_data = models.OneToOneField(
        HECMInput,
        on_delete=models.CASCADE,
        related_name="result"
    )
    config_used = models.ForeignKey(
        HECMConfig,
        on_delete=models.PROTECT,
        help_text="Configuration used for this calculation"
    )
    max_claim_amount = models.DecimalField(max_digits=12, decimal_places=2)
    principal_limit_factor = models.DecimalField(max_digits=6, decimal_places=5)
    principal_limit = models.DecimalField(max_digits=12, decimal_places=2)
    origination_fee = models.DecimalField(max_digits=8, decimal_places=2)
    mortgage_insurance_premium = models.DecimalField(max_digits=12, decimal_places=2)
    other_closing_costs = models.DecimalField(max_digits=12, decimal_places=2)
    total_closing_costs = models.DecimalField(max_digits=12, decimal_places=2)
    max_cash_out = models.DecimalField(max_digits=12, decimal_places=2)