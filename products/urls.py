from django.urls import path
from . import views

urlpatterns = [
    path('', views.welcome, name="welcome"),
    path('home/', views.home, name="home"),
    path('products/', views.productshome, name="products-home"),
    path('services/', views.serviceshome, name="services-home"),
]