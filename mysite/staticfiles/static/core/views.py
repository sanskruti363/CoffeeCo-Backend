import datetime
from numbers import Number
import uuid
from django.core.mail import send_mail
import random
import string
from rest_framework import exceptions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from core.serializers import OrderSerializer, ProductSerializer, UserSerializer
from core.models import Order, ProductDetails, Reset, User, UserToken
from core.authentication import (
    JWTAuthentication,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
)
import razorpay
from django.shortcuts import render
from django.http import JsonResponse
from decouple import config
from django.views.decorators.csrf import csrf_exempt


# Create your views here.
class RegisterAPIView(APIView):
    def post(self, request):
        data = request.data

        if data["password"] != data["password_confirm"]:
            raise exceptions.APIException("Password do not match")

        serializer = UserSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)


class LoginAPIView(APIView):
    def post(self, request):
        email = request.data["email"]
        password = request.data["password"]

        user = User.objects.filter(email=email).first()

        if user is None:
            raise exceptions.AuthenticationFailed(
                {"status": False, "data": {"Invalid credentials"}}
            )
        if not user.check_password(password):
            raise exceptions.AuthenticationFailed(
                {"status": False, "data": {"Invalid credentials"}}
            )

        access_token = create_access_token(user.id)
        refresh_token = create_refresh_token(user.id)

        UserToken.objects.create(
            user_id=user.id,
            token=refresh_token,
            expired_at=datetime.datetime.utcnow() + datetime.timedelta(days=7),
        )

        response = Response()
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            samesite="None",
            httponly=True,
            secure=True,
        )
        response.data = {"token": access_token, "success": True}
        return response


class UserAPIView(APIView):
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        return Response({"status": True, "data": UserSerializer(request.user).data})


class IsUserAdmin(APIView):
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        user_data = UserSerializer(request.user).data
        is_admin = user_data.is_admin
        return Response({"isAdmin": is_admin})


class RefreshAPIView(APIView):
    def post(self, request):
        refresh_token = request.COOKIES.get("refresh_token")
        id = decode_refresh_token(refresh_token)
        current_utc_time = datetime.datetime.utcnow()
        if not UserToken.objects.filter(
            user_id=id,
            token=refresh_token,
            expired_at__gt=current_utc_time,
        ).exists():
            raise exceptions.AuthenticationFailed("Unauthenticated")

        access_token = create_access_token(id)
        return Response({"token": access_token})


class LogoutAPIView(APIView):
    def post(self, request):
        try:
            refresh_token = request.COOKIES.get("refresh_token")
            if refresh_token:
                # Validate and delete the refresh token
                UserToken.objects.filter(token=refresh_token).delete()

                # Clear the cookie on the response
                response = Response({"message": "success"})
                response.delete_cookie(
                    key="refresh_token"
                )  # Set secure attribute if using HTTPS
                return response
            else:
                return Response(
                    {"message": "No refresh_token found"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except Exception as e:
            return Response(
                {"message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ForgotAPIView(APIView):
    def post(self, request):

        email = request.data["email"]
        token = "".join(
            random.choice(string.ascii_lowercase + string.digits) for _ in range(10)
        )

        Reset.objects.create(email=request.data["email"], token=token)

        url = "http://localhost:4200/auth/reset/" + token

        send_mail(
            subject="Reset password!",
            message='Click <a href="%s">here</a> to reset your password' % url,
            from_email="from@example.com",
            recipient_list=[email],
        )

        return Response({"message": "success"})


class ResetAPIView(APIView):
    def post(self, request):
        data = request.data

        if data["password"] != data["password_confirm"]:
            raise exceptions.APIException("Password do not match")

        reset_password = Reset.objects.filter(token=data["token"]).first()

        if not reset_password:
            raise exceptions.APIException("Invalid link")

        user = User.objects.filter(email=reset_password.email).first()

        if not user:
            raise exceptions.APIException("User not found")

        user.set_password(data["password"])
        user.save()

        return Response({"message": "success"})


class ProductListView(APIView):
    # authentication_classes = [JWTAuthentication]

    def get(self, request):
        products = ProductDetails.objects.all()
        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data)


class AddProduct(APIView):
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        data = request.data
        data['product_id'] = str(uuid.uuid4())
        serializer = ProductSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


razorpay_client = razorpay.Client(auth=(config('RAZORPAY_API_KEY'), config('RAZORPAY_SECRET_KEY')))

class CreateOrder(APIView):
    def post(self, request):
        actual_amount = calculate_order_amount(request)
        amount = int(actual_amount * 100)  # Amount in paise
        currency = 'INR'
        receipt = "receiptId_01"
        order = razorpay_client.order.create(dict(amount=amount, currency=currency, receipt=receipt))
        return Response({'order_id': order['id']})

class VerifyPayment(APIView):
    def post(self, request):
        payment_id = request.data.get('razorpay_payment_id')
        order_id = request.data.get('razorpay_order_id')
        signature = request.data.get('razorpay_signature')

        user_data = {
            'first_name': request.data.get('first_name'),
            'last_name': request.data.get('last_name'),
            'email': request.data.get('email'),            
        }

        params_dict = {
            'razorpay_order_id': order_id,
            'razorpay_payment_id': payment_id,
            'razorpay_signature': signature
        }

        result = razorpay_client.utility.verify_payment_signature(params_dict)
        if result is not None:
            try:
                order = Order.objects.get(order_id=order_id)
            except Order.DoesNotExist:
                order = Order(order_id=order_id) 

            order.payment_id = payment_id
            order.status = 'PAID'
            order.email = user_data.get('email')
            order.save()  
            return JsonResponse({'status': 'success', 'payment_id': payment_id})
        else:
            return JsonResponse({'status': 'failure'})
    

class FetchOrders(APIView):
    authentication_classes = [JWTAuthentication]
    def post(self, request):
        user_data = UserSerializer(request.user).data
        email = user_data.get('email')
        orders = Order.objects.filter(email=email)
        serialized_orders = OrderSerializer(orders, many=True).data
        return Response({'orders': serialized_orders})

def calculate_order_amount(request):
    if 'product_id' in request.data:
        product = ProductDetails.objects.get(product_id=request.data['product_id'])
        return product.price
    else:
        return 0 