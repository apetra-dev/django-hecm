from decimal import Decimal
from ..models.config import HECMConfig
from ..models.inputs import HECMInput
from ..models.results import HECMResult
from ..models.tables import PLFTable
import logging
logger = logging.getLogger('myhecmapp')

class HECMCalculator:
    """Service class that performs HECM calculations"""

    def __init__(self, input_data, config=None):
        """
        Initialize calculator with input data and optional config

        Args:
            input_data: HECMInput instance or dict with input parameters
            config: Optional HECMConfig instance (uses latest by default)
        """
        if isinstance(input_data, dict):
            # Convert all numeric values to Decimal
            input_dict = {}
            for key, value in input_data.items():
                if key in ['home_value', 'interest_rate', 'existing_mortgage'] and value is not None:
                    input_dict[key] = Decimal(str(value))
                else:
                    input_dict[key] = value

            self.input_data = HECMInput(**input_dict)
            if not self.input_data.pk:  # If it's a new instance that hasn't been saved
                self.input_data._state.adding = True  # Mark as a new instance
        else:
            self.input_data = input_data

        self.config = config or HECMConfig.get_current()

    def get_principal_limit_factor(self):
        """
        Get Principal Limit Factor from table or approximation
        """
        logger.info(
            f"Calculating principal limit factor for age={self.input_data.age}, rate={self.input_data.interest_rate}")

        try:
            # Try to find exact match in PLF table
            plf_entry = PLFTable.objects.get(
                config=self.config,
                age=self.input_data.age,
                interest_rate=self.input_data.interest_rate
            )
            logger.info(f"Found PLF in table: {plf_entry.factor}")
            return plf_entry.factor
        except PLFTable.DoesNotExist:
            # Fallback to approximation
            logger.info("No exact PLF match found in table, using approximation formula")
            base_factor = min(Decimal('0.75'),
                              (Decimal(str(self.input_data.age)) - Decimal('62')) * Decimal('0.005') + Decimal('0.35'))
            rate_adjustment = max(Decimal('0'), (self.input_data.interest_rate - Decimal('5.0')) * Decimal('0.1'))
            result = max(Decimal('0.2'), base_factor - rate_adjustment)
            logger.info(f"Calculated PLF using approximation: {result}")
            return result

    def get_max_claim_amount(self):
        """Calculate the maximum claim amount"""
        return min(self.input_data.home_value, self.config.fha_lending_limit)

    def calculate_origination_fee(self):
        """Calculate origination fee based on tiered structure"""
        if self.input_data.home_value <= self.config.first_tier_limit:
            fee = max(
                self.config.origination_fee_min,
                self.input_data.home_value * self.config.first_tier_rate
            )
        else:
            fee = (self.config.first_tier_limit * self.config.first_tier_rate +
                   (self.input_data.home_value - self.config.first_tier_limit) *
                   self.config.second_tier_rate)

        return min(fee, self.config.origination_fee_cap)

    def calculate_mortgage_insurance_premium(self):
        """Calculate upfront Mortgage Insurance Premium"""
        return self.get_max_claim_amount() * self.config.mip_rate

    def estimate_other_closing_costs(self):
        """Estimate other closing costs (appraisal, title, etc.)"""
        # Simple estimate - could be made more sophisticated
        return Decimal('3000.00')

    def calculate_total_closing_costs(self):
        """Calculate total closing costs"""
        origination_fee = self.calculate_origination_fee()
        mip = self.calculate_mortgage_insurance_premium()
        other_costs = self.estimate_other_closing_costs()
        return origination_fee + mip + other_costs

    def calculate_principal_limit(self):
        """Calculate principal limit"""
        max_claim = self.get_max_claim_amount()
        plf = self.get_principal_limit_factor()
        return max_claim * plf

    def calculate_max_cash_out(self):
        """Calculate maximum cash out available"""
        principal_limit = self.calculate_principal_limit()
        closing_costs = self.calculate_total_closing_costs()
        max_cash_out = max(Decimal('0'), principal_limit - self.input_data.existing_mortgage - closing_costs)
        return max_cash_out

    def calculate(self):
        """Perform all calculations and return result object"""
        # Create a simple dict result since we may not be able to save to the database in this case
        result = {
            "input_data": self.input_data,
            "config_used": self.config,
            "max_claim_amount": self.get_max_claim_amount(),
            "principal_limit_factor": self.get_principal_limit_factor(),
            "principal_limit": self.calculate_principal_limit(),
            "origination_fee": self.calculate_origination_fee(),
            "mortgage_insurance_premium": self.calculate_mortgage_insurance_premium(),
            "other_closing_costs": self.estimate_other_closing_costs(),
            "total_closing_costs": self.calculate_total_closing_costs(),
            "max_cash_out": self.calculate_max_cash_out()
        }

        return result

    def get_result_dict(self):
        """Calculate and return results as a dictionary"""
        result = self.calculate()
        return {
            "principal_limit": float(result["principal_limit"]),
            "max_cash_out": float(result["max_cash_out"]),
            "max_origination_fee": float(result["origination_fee"]),
            "max_claim_amount": float(result["max_claim_amount"]),
            "principal_limit_factor": float(result["principal_limit_factor"]),
            "mortgage_insurance_premium": float(result["mortgage_insurance_premium"]),
            "other_closing_costs": float(result["other_closing_costs"]),
            "total_closing_costs": float(result["total_closing_costs"])
        }

