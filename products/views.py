from django.shortcuts import render
from .models import Product, Cart, CartItem, Order, OrderItem
from .serializers import ProductSerializer, CartSerializer, OrderSerializer
from .permissions import IsVendorUser
from rest_framework import viewsets, permissions, status
from rest_framework.permissions  import IsAuthenticated 
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db import transaction

# Create your views here.
class ProductViewSet(viewsets.ModelViewSet):
    """Product viewset (create, list, delete)"""
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    look_up_field = 'slug'
    filterset_fiels = ['price', 'vendor']
    search_fields = ['name', 'description']
    ordering_fields = ['price', 'created_at']
    
    def get_permissions(self):
        """checks if user is authorised to perform some actions"""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsVendorUser()]
        return [permissions.AllowAny()]

    def perform_create(self, serializer):
        """set the vendor to the current user when creating a product"""
        serializer.save(vendor=self.request.user)
    

class CartViewSet(viewsets.ModelViewSet):
    """Cart class based viewset"""
    permission_classes = [IsAuthenticated]
    queryset = Cart.objects.all()
    serializer_class = CartSerializer

    def get_queryset(self):
        """helper function to get or create cart if not exist"""
        return Cart.objects.filter(user=self.request.user)
    
    
    @action(detail=False, methods=['post'], url_path='add') # custom view in viewset
    def add_to_cart(self, request):
        """adds item to cart"""
        product_id = request.data.get('product')
        quantity = int(request.data.get('quantity', 1)) # gets quantity and typecast to int oruse 1(default)

        if not product_id:
            return Response({'error':'Product ID is required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({'error':'Product does not exist'}, status=status.HTTP_404_NOT_FOUND)
        
        cart, _ = Cart.objects.get_or_create(user=request.user)

        cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product, defaults={'price': product.price, 'quantity': quantity})
        if not created:
            cart_item.quantity += quantity
            cart_item.save()
        return Response({'Message':'Item added to cart'})

    @action(detail=True, methods=['patch'], url_path='update')
    def update_quantity(self, request, pk=None):
        """updates the quntity of a product in cart""" 
        try:
            cart_item = CartItem.objects.get(id=pk, cart__user=request.user)
        except CartItem.DoesNotExist:
            return Response({'error':'Item not found in cart'}, status=status.HTTP_404_NOT_FOUND)
        
        try:
            quantity = int(request.data.get('quantity',1))
        except (ValueError, TypeError):
            return Response({'error':'Invalid quantity'}, status=status.HTTP_400_BAD_REQUEST)
        if quantity <= 0:
            return Response({'error':'Quantity must be greater than 0'}, status=status.HTTP_400_BAD_REQUEST)
        if quantity > cart_item.product.stock:
            return Response({'error':'Insufficient stock'}, status=status.HTTP_400_BAD_REQUEST)
        # update the quantity of the cart item
        cart_item.quantity = quantity
        cart_item.save()
        return Response({'message':f'Item quantity updated to {cart_item.quantity}'})

    @action(detail=True, methods=['delete'], url_path='remove')
    def remove_item(self, request, pk):
        """removes the item from cart"""
        try:
            cart_item = CartItem.objects.get(id=pk, cart__user=request.user)
            cart_item.delete()
            return Response({'message':'Item removed from cart'})
        except CartItem.DoesNotExist:
            return Response({'error':'Item not found in cart'}, status=status.HTTP_404_NOT_FOUND)
        

class OrderViewSet(viewsets.ModelViewSet):
    """order viewset"""
    permission_classes = [IsAuthenticated]
    serializer_class = OrderSerializer
    def get_queryset(self):
        """gets user orders"""
        return Order.objects.filter(user=self.request.user).prefetch_related('items__product')

    @action(detail=False, methods=['post'], url_path='checkout')
    @transaction.atomic # to ensure DB interury in case error occur when ceating order 
    def checkout(self, request):
        """checkout user's cart to order"""
        user = request.user
        # gets the user cart
        try:
            cart = Cart.objects.get(user=user)
        except Cart.DoesNotExist:
            return Response({'error':'Cart not found'}, status=status.HTTP_400_BAD_REQUEST)
        
        # gets the items in cart
        cart_items = cart.items.all()
        if not cart_items:
            return Response({'error':'Cart is empty'}, status=status.HTTP_400_BAD_REQUEST)
        
        order = Order.objects.create(user=user, total=0)
        total_price = 0

        # changes the cart items to order items for each 
        for item in cart_items:
            subtotal = item.quantity * item.price
            total_price += subtotal

            OrderItem.objects.create(order=order, product=item.product, quantity=item.quantity, price=item.price)
        order.total = total_price
        order.save()
 
        # clears the cart
        cart.items.all().delete()

        # turns the order into JSON
        serializer = OrderSerializer(order)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    # still needs testing
    @action(detail='False', methods=['get'], url_path='vendor-orders')
    def vendor_orders(self, request):
        """List the orders for the currrent vendor"""
        vendor = request.user
        orders = Order.objects.filter(items__product__vendor=vendor).distinct().prefetch_related('items__product')

        serializer = self.get_serializer(orders, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], url_path='update-status')
    def update_status(self, request, pk=None):
        """update the order status of the product"""
        order = self.get_object() # gets the model object

        if not request.user.is_staff and not order.items.filter(product__vendor=request.user).exists():
            return Response({"error":"You are not authorised to do this"}, status=status.HTTP_404_NOT_FOUND)
        order_status = request.data.get('status')
        if order_status not in dict(Order.STATUS_CHOICES):
            return Response({'error':'Invalid order status choice'}, status=status.HTTP_400_BAD_REQUEST)
        order.status = order_status
        order.save()
        return Response({'message':f'Order {order.id} status updated successfully'})
    
