from django.urls import path
from core.views import AddProduct, FetchOrders, ProductListView, RegisterAPIView, LoginAPIView, UserAPIView, RefreshAPIView, LogoutAPIView, ForgotAPIView, ResetAPIView, VerifyPayment, CreateOrder

urlpatterns = [
    path("register", RegisterAPIView.as_view()),
    path("login", LoginAPIView.as_view()),
    path("user", UserAPIView.as_view()),
    path("add-product", AddProduct.as_view()),
    path("get-products", ProductListView.as_view()),
    path("refresh", RefreshAPIView.as_view()),
    path("logout", LogoutAPIView.as_view()),
    path("forgot", ForgotAPIView.as_view()),
    path("reset", ResetAPIView.as_view()),
    path("create-order", CreateOrder.as_view()),
    path('verify-payment', VerifyPayment.as_view()),
    path('fetch-orders', FetchOrders.as_view()),
]
