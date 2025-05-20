from django.urls import path
from . import views

app_name = 'myhecmapp'

urlpatterns = [
    path('calculate/', views.calculate_hecm, name='calculate'),
]
