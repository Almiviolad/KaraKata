from django.shortcuts import render
from rest_framework import viewsets, permissions
from .serializers import ShippingSerializer
from .models import ShippingAddress

# Create your views here.
class ShippingAddressViewset(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ShippingSerializer

    def get_queryset(self):
        """ensures only users' adresses can be CRUD by user"""
        return ShippingAddress.objects.filter(user=self.request.user)