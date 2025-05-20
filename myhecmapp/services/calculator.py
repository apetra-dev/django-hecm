from decimal import Decimal
from ..models.config import HECMConfig
from ..models.inputs import HECMInput
from ..models.results import HECMResult
from ..models.tables import PLFTable
import logging
import pandas as pd
import os

logger = logging.getLogger('myhecmapp')


class HECMCalculator:
    """Service class that performs HECM calculations"""

    # Class variable to cache CSV data
    _plf_data = None

    @classmethod
    def load_plf_data(cls, csv_path=None):
        """
        Load PLF data from CSV file into a pandas DataFrame

        Args:
            csv_path: Path to the CSV file (optional)

        Returns:
            DataFrame with PLF data
        """
        if cls._plf_data is not None:
            return cls._plf_data

        if csv_path is None:
            # Default path - adjust according to your project structure
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            csv_path = os.path.join(base_dir, 'data', 'consolidated_2017_plfs copy.csv')

        try:
            logger.info(f"Loading PLF data from CSV file: {csv_path}")
            cls._plf_data = pd.read_csv(csv_path)
            logger.info(f"Successfully loaded PLF data with {len(cls._plf_data)} entries")
            return cls._plf_data
        except Exception as e:
            logger.error(f"Error loading PLF data: {str(e)}")
            # Return empty DataFrame as fallback
            return pd.DataFrame(columns=['Age', 'Rate', 'PLF'])

    def __init__(self, input_data, config=None, index_rate=None):
        """
        Initialize calculator with input data and optional config

        Args:
            input_data: HECMInput instance or dict with input parameters
            config: Optional HECMConfig instance (uses latest by default)
            index_rate: Optional index rate (defaults to 10-year LIBOR or similar index)
        """
        if isinstance(input_data, dict):
            # Convert all numeric values to Decimal
            input_dict = {}
            for key, value in input_data.items():
                if key in ['home_value', 'interest_rate', 'existing_mortgage', 'margin'] and value is not None:
                    input_dict[key] = Decimal(str(value))
                else:
                    input_dict[key] = value

            # If margin is provided but interest_rate is not, calculate interest_rate
            if 'margin' in input_dict and 'interest_rate' not in input_dict:
                if index_rate is None:
                    # Default index rate if not provided
                    index_rate = Decimal('3.50')
                input_dict['interest_rate'] = index_rate + input_dict['margin']
                logger.info(
                    f"Calculated interest rate: {input_dict['interest_rate']} (index {index_rate} + margin {input_dict['margin']})")

            # If no margin provided but we have interest_rate and index_rate, calculate margin
            elif 'interest_rate' in input_dict and 'margin' not in input_dict and index_rate is not None:
                input_dict['margin'] = input_dict['interest_rate'] - index_rate
                logger.info(
                    f"Calculated margin: {input_dict['margin']} (rate {input_dict['interest_rate']} - index {index_rate})")

            # Default margin if not provided
            elif 'margin' not in input_dict:
                input_dict['margin'] = Decimal('2.00')  # Default 2% margin
                logger.info(f"Using default margin of 2.00%")

            self.input_data = HECMInput(**input_dict)
            if not self.input_data.pk:  # If it's a new instance that hasn't been saved
                self.input_data._state.adding = True  # Mark as a new instance
        else:
            self.input_data = input_data

        self.config = config or HECMConfig.get_current()
        self.index_rate = index_rate

        # Load PLF data when initializing
        self.__class__.load_plf_data()

    def get_principal_limit_factor(self):
        """
        Get Principal Limit Factor from table or approximation
        """
        logger.info(
            f"Calculating principal limit factor for age={self.input_data.age}, rate={self.input_data.interest_rate}")

        try:
            # First try to find exact match in PLF table from database
            plf_entry = PLFTable.objects.get(
                config=self.config,
                age=self.input_data.age,
                interest_rate=self.input_data.interest_rate
            )
            logger.info(f"Found PLF in database table: {plf_entry.factor}")
            return plf_entry.factor
        except PLFTable.DoesNotExist:
            # Database lookup failed, now try CSV data
            logger.info("No match in database, checking CSV data...")

            try:
                # Get the PLF data
                plf_data = self.__class__._plf_data

                if plf_data is not None and not plf_data.empty:
                    # Try exact match in the CSV data
                    exact_match = plf_data[(plf_data['Age'] == self.input_data.age) &
                                           (abs(plf_data['Rate'] - float(self.input_data.interest_rate)) < 0.001)]

                    if not exact_match.empty:
                        plf = Decimal(str(exact_match.iloc[0]['PLF']))
                        logger.info(f"Found exact PLF match in CSV: {plf}")
                        return plf

                    # If no exact match, find closest
                    logger.info("No exact match in CSV, finding closest match...")

                    # Filter by age first
                    age_matches = plf_data[plf_data['Age'] == self.input_data.age]

                    if not age_matches.empty:
                        # Find closest interest rate
                        age_matches['rate_diff'] = abs(age_matches['Rate'] - float(self.input_data.interest_rate))
                        closest_match = age_matches.loc[age_matches['rate_diff'].idxmin()]
                        plf = Decimal(str(closest_match['PLF']))
                        logger.info(
                            f"Found closest PLF in CSV by interest rate: {plf} (rate diff: {closest_match['rate_diff']})")
                        return plf

                logger.info("No suitable match found in CSV, using approximation formula")
            except Exception as e:
                logger.error(f"Error using CSV data: {str(e)}")
                logger.info("Falling back to approximation formula due to error")

            # Fallback to approximation
            logger.info("Using approximation formula")
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
            "max_cash_out": self.calculate_max_cash_out(),
            "margin": getattr(self.input_data, 'margin', Decimal('2.00')),
            "index_rate": self.index_rate or Decimal('3.50')
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
            "total_closing_costs": float(result["total_closing_costs"]),
            "margin": float(getattr(self.input_data, 'margin', Decimal('2.00'))),
            "index_rate": float(self.index_rate or Decimal('3.50')),
            "interest_rate": float(self.input_data.interest_rate)
        }

    def recalculate_with_margin(self, margin, index_rate=None):
        """
        Recalculate using a different margin value

        Args:
            margin: New margin value to use
            index_rate: Optional index rate to use (uses instance value if not provided)

        Returns:
            Dictionary with recalculated results
        """
        if index_rate is None:
            index_rate = self.index_rate or Decimal('3.50')

        # Calculate new interest rate
        new_interest_rate = index_rate + Decimal(str(margin))
        logger.info(f"Recalculating with new margin: {margin}%, new rate: {new_interest_rate}%")

        # Create new input data with the updated interest rate
        new_input = {
            'age': self.input_data.age,
            'home_value': self.input_data.home_value,
            'interest_rate': new_interest_rate,
            'margin': Decimal(str(margin)),
            'existing_mortgage': self.input_data.existing_mortgage
        }

        # Create a new calculator with the updated inputs
        new_calculator = HECMCalculator(new_input, self.config, index_rate)

        # Return the results
        return new_calculator.get_result_dict()

