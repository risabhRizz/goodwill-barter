from django.urls import path
from .views import (
    ProductListView,
    ProductDetailView,
    ProductCreateView,
    ProductUpdateView,
    ProductDeleteView,
    UserProductListView
)
from . import views

urlpatterns = [
    path('', views.home, name="home"),
    path('products/', ProductListView.as_view(), name="products-home"),
    path('user/<str:username>', UserProductListView.as_view(), name="user-products"),
    path('products/product/<int:pk>/', ProductDetailView.as_view(), name="product-detail"),
    path('products/product/new/', ProductCreateView.as_view(), name="product-create"),
    path('products/product/<int:pk>/update', ProductUpdateView.as_view(), name="product-update"),
    path('products/product/<int:pk>/delete', ProductDeleteView.as_view(), name="product-delete"),
    path('services/', views.serviceshome, name="services-home"),
]
