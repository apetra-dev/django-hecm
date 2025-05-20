from django.shortcuts import render
from django.http import JsonResponse
from .services.calculator import HECMCalculator
from .models.inputs import HECMInput
from decimal import Decimal, InvalidOperation
import traceback


def calculate_hecm(request):
    """View to handle HECM calculations"""
    if request.method == 'POST':
        # For API requests
        try:
            # Get form data and convert to appropriate types
            try:
                home_value = Decimal(request.POST.get('home_value', '0'))
            except InvalidOperation:
                home_value = Decimal('0')

            try:
                age = int(request.POST.get('age', '0'))
            except ValueError:
                age = 0

            try:
                interest_rate = Decimal(request.POST.get('interest_rate', '0'))
            except InvalidOperation:
                interest_rate = Decimal('0')

            try:
                existing_mortgage = Decimal(request.POST.get('existing_mortgage', '0'))
            except InvalidOperation:
                existing_mortgage = Decimal('0')

            # Use calculator to get results
            calculator = HECMCalculator({
                'home_value': home_value,
                'age': age,
                'interest_rate': interest_rate,
                'existing_mortgage': existing_mortgage
            })

            results = calculator.get_result_dict()
            return JsonResponse({'success': True, 'results': results})
        except Exception as e:
            error_traceback = traceback.format_exc()
            print(f"Error: {str(e)}")
            print(f"Traceback: {error_traceback}")
            return JsonResponse({
                'success': False,
                'error': str(e),
                'traceback': error_traceback
            })
    else:
        # For GET requests, show the calculator form
        return render(request, 'myhecmapp/calculator.html')
