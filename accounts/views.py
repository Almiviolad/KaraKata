from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import CustomTokenObtainPairSerializer, RegisterSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

# Create your views here.
class CustomLoginView(TokenObtainPairView):
    """Handles login using JWT and obtains JWT token with role also  logs user in."""
    serializer_class = CustomTokenObtainPairSerializer

class RegisterView(APIView):
    """register users with form details and uses serilizer to validate data"""
    def post(self, request):
        # Implement registration logic here
        data = request.data
        serializer = RegisterSerializer(data=data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response(
                {
                    'user': serializer.data,
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                },
                status=status.HTTP_201_CREATED
            )
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)