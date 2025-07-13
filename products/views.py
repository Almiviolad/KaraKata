from django.shortcuts import render
from .models import Product, Cart, CartItem, Order, OrderItem
from .serializers import ProductSerializer, CartSerializer, OrderSerializer, OrderItemSerializer, VendorOrderItemSerializer, VendorOrderSerializer
from .permissions import IsVendorUser
from rest_framework import viewsets, permissions, status
from rest_framework.permissions  import IsAuthenticated 
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.views import APIView
from django.db import transaction
from shipping.models import ShippingAddress
from django.utils import timezone

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
        
class OrderItemViewSet(viewsets.ModelViewSet):
    """order viewset"""
    permission_classes = [IsAuthenticated]
    serializer_class = OrderItemSerializer
    def get_queryset(self):
        """gets vendors orders"""
        return OrderItem.objects.filter(product__vendor=self.request.user)
    
    @action(detail=True, methods=['post'], url_path='update-item-status')
    def update_item_status(self, request, pk=None):
        """update the order item status of the product"""
        order_item = self.get_object() # gets the model object

        if not request.user.is_staff and not order_item.filter(product__vendor=request.user).exists():
            return Response({"error":"You are not authorised to do this"}, status=status.HTTP_404_NOT_FOUND)
        order_status = request.data.get('status')
        if order_status not in dict(OrderItem.STATUS_CHOICES):
            return Response({'error':'Invalid order status choice'}, status=status.HTTP_400_BAD_REQUEST)
        order_item.status = order_status
        order_item.save()
        return Response({'message':f'Order item {order_item.id} status updated successfully'})
    
    @action(detail=True, methods=['post'], url_path='update_delivery')
    def update_is_delivered(self, request, pk=None):
        """Update delivery status"""
        order_item = self.get_object() # gets the model object

        if not request.user.is_staff and not order_item.filter(product__vendor=request.user).exists():
            return Response({"error":"You are not authorised to do this"}, status=status.HTTP_404_NOT_FOUND)
        is_delivered = request.data.get('is_delivered')
        order_item.is_delivered = is_delivered
        order_item.save()
        return Response({'message':f'Order item {order_item.id} delivery status updated successfully'})
    
        

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
        address_id = request.data.get('shipping_address_id')
        # gets the user cart
        try:
            cart = Cart.objects.get(user=user)
        except Cart.DoesNotExist:
            return Response({'error':'Cart not found'}, status=status.HTTP_400_BAD_REQUEST)
        
        # gets the items in cart
        cart_items = cart.items.all()
        if not cart_items:
            return Response({'error':'Cart is empty'}, status=status.HTTP_400_BAD_REQUEST)
        

        try:
             address = ShippingAddress.objects.get(id=address_id, user=user)
        except ShippingAddress.DoesNotExist:
            return Response({'error':'Invalid shipping address'}, status=status.HTTP_400_BAD_REQUEST)
        
        order = Order.objects.create(user=user, shipping_address=address, total=0)
        total_price = 0

        # changes the cart items to order items for each 
        for item in cart_items:
            subtotal = item.quantity * item.price
            total_price += subtotal

            OrderItem.objects.create(order=order, product=item.product, quantity=item.quantity, price=item.price, vendor=item.product.vendor, status='pending')
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
    
class VendorDashboardView(APIView):
    """vENDOR DASHBOARD VIEW"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        vendor_items = OrderItem.objects.filter(vendor=request.user, order__is_paid=True).select_related('order','product', 'order__user')
        print(vendor_items)
        order_map = {}

        for item in vendor_items:
            order = item.order
            quantity = item.quantity
            price = item.price

            if order.id not in order_map:
                order_map[order.id] = {
                    'order_id': order.id,
                    'customer': order.user.email,
                    'order_status': order.status,
                    'quantity': quantity,
                    'price':price,
                    'created_at': order.created_at,
                    'shipping_address': order.shipping_address,
                    'items': []
                }
            order_map[order.id]['items'].append(item) # adds vendor items tothe item array in order

        response_data = []
        for order_data in order_map.values():
            item_serializer = VendorOrderItemSerializer(order_data['items'], many=True)
            order_data['items'] = item_serializer.data

            order_data = VendorOrderSerializer(order_data)

            response_data.append(order_data.data)
        return Response({'orders': response_data}, status=status.HTTP_200_OK)
# To Do: implement order total and total earnng forvendor

class InitPaymentView(APIView):
    """Initialise payment"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, order_id):
        """gets order create new payment"""
        try:
            order = Order.objects.get(id=order_id, user=request.user)
            if order.is_paid:
                return Response({'message': 'Order already paid'}, status=400)
            
            # Fake transcatiomn ref we later generate from paysatck init call
            fake_ref = f"txn_{order_id}_{timezone.now().timestamp()}"
            order.payment_reference = fake_ref
            order.save()

            # when addinfg payment return redirectt url
            return Response({"message":"Payment initialized succesfully", "reference":fake_ref, "amount":order.total, "callback_url":f"http://localhost:8000/api/{order.id}/verify-payment/"})
        except Order.DoesNotExist:
            return Response({"error":"Order not found"}, status=404)

class VerifyPaymentView(APIView):
    """verify payment (simulated for now)"""
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        """gets order and verify payment"""
        try:
            order = Order.objects.get(id=order_id, user=request.user)
            if not order.is_paid:
                #add real payment api call later
                order.is_paid = True
                order.paid_at = timezone.now()
                order.save()
            for item in order.items.all():
                item.product.stock -= item.quantity
                item.product.save()
            # call the payment gateway API to verify the payment

            return Response({'message': 'Payment verified successfully'}, status=status.HTTP_200_OK)
        except Order.DoesNotExist:
            return Response({'error':'Order not found'}, status=404)