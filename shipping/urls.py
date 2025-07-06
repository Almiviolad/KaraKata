from rest_framework.routers import DefaultRouter
from .views import ShippingAddressViewset

router = DefaultRouter()
router.register(r'addresses', ShippingAddressViewset, basename='shipping-address')
                
urlpatterns= router.urls