from rest_framework.serializers import ModelSerializer
from core.models import Order, User, ProductDetails


class UserSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "first_name", "last_name", "email", "password", "is_superuser"]
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        instance = self.Meta.model(**validated_data)

        if password is not None:
            instance.set_password(password)

        instance.save()
        return instance


class ProductSerializer(ModelSerializer):
    class Meta:
        model = ProductDetails
        fields = ['product_id', 'title', 'description', 'price', 'quantity_available', 'image_url']

class OrderSerializer(ModelSerializer):
    class Meta:
        model = Order
        fields = '__all__'  