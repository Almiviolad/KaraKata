from rest_framework import serializers
from .models import Product, Cart, CartItem, OrderItem, Order, Category
from shipping.serializers import ShippingSerializer
from shipping.models import ShippingAddress
from shipping.serializers import ShippingSerializer

class ProductSerializer(serializers.ModelSerializer):
    """turns products model to json"""
    class Meta:
        model = Product
        fields = "__all__"
        read_only_fields = ['id', 'created_at', 'slug', 'vendor']



class CartItemSerializer(serializers.ModelSerializer):
    """cart item serializer"""
    product_name = serializers.CharField(source="product.name", read_only=True)
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ['id', 'product', 'product_name', 'price', 'subtotal', 'quantity',]
        read_only_fields = ['price', 'product_name']

    def get_subtotal(self, obj): # here the objis the model for this method
        return obj.quantity * obj.price 


class CartSerializer(serializers.ModelSerializer):
    """Cart serializer"""
    items = CartItemSerializer(many=True, read_only=True) # nested serializer for items in cart
    total = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ['user', 'created_at', 'id', 'items', 'total']
        read_only_fields = ['id', 'created_at', 'total', 'user']

    def get_total(self, obj):
        return obj.total
    
class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    status = serializers.CharField()
    
    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'quantity', 'price', 'status', 'vendor', 'is_delivered']
        read_only_fields = ['id', 'product', 'vendor']

class VendorOrderItemSerializer(serializers.ModelSerializer):
    product = serializers.StringRelatedField(source='product.name', read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'quantity', 'price', 'status', 'vendor']
        read_only_fields = ['id', 'product', 'vendor']

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    status = serializers.CharField()  # Display the status choice label
    shipping_address = ShippingSerializer(read_only=True)  # Use the ShippingSerializer for address details

    class Meta:
        model = Order
        fields = ['id', 'created_at', 'is_paid', 'status', 'total', 'items', 'shipping_address', 'cancelled']
        read_only_fields = ['id', 'created_at', 'status']


class VendorOrderSerializer(serializers.Serializer):
    order_id = serializers.IntegerField()
    customer = serializers.EmailField()
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    order_status = serializers.CharField()
    items = VendorOrderItemSerializer(many=True, read_only=True)
    shipping_address = ShippingSerializer()

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = "__all__"


