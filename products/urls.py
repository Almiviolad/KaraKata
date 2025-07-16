from rest_framework.routers import DefaultRouter
from .views import ProductViewSet, CartViewSet, OrderViewSet, OrderItemViewSet, VendorDashboardView, InitPaymentView, VerifyPaymentView, CategoryViewset
from rest_framework.urls import path
router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='product')
router.register(r'cart', CartViewSet, basename='cart')
router.register(r'orders', OrderViewSet, basename='orders')
router.register(r'categories', CategoryViewset, basename='category')
router.register(r'order-items', OrderItemViewSet, basename='order-items')

urlpatterns = router.urls 
urlpatterns += [
    path('vendor-dashboard/', VendorDashboardView.as_view()),
    path('<int:order_id>/init-payment/', InitPaymentView.as_view(), name='initialize_payment'),
    path('<int:order_id>/verify-payment/', VerifyPaymentView.as_view(), name='verify_payment'),
]