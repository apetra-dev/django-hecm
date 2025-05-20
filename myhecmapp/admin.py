from django.contrib import admin
from .models.config import HECMConfig
from .models.inputs import HECMInput
from .models.results import HECMResult
from .models.tables import PLFTable

@admin.register(HECMConfig)
class HECMConfigAdmin(admin.ModelAdmin):
    list_display = ('effective_date', 'fha_lending_limit', 'min_age')
    list_filter = ('effective_date',)

@admin.register(PLFTable)
class PLFTableAdmin(admin.ModelAdmin):
    list_display = ('config', 'age', 'interest_rate', 'factor')
    list_filter = ('age', 'interest_rate')
    search_fields = ('age', 'interest_rate')

@admin.register(HECMInput)
class HECMInputAdmin(admin.ModelAdmin):
    # Removed 'created_at' which doesn't exist in your model
    list_display = ('id', 'home_value', 'age', 'interest_rate', 'existing_mortgage')
    # Removed 'created_at' from list_filter
    list_filter = ('age',)
    search_fields = ('home_value', 'age')

@admin.register(HECMResult)
class HECMResultAdmin(admin.ModelAdmin):
    list_display = ('input_data', 'principal_limit', 'max_cash_out')
    list_filter = ('config_used',)

