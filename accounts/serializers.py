
from rest_framework import serializers
from .models import CustomUser
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
  """handles login using jwt and obtaon jwt token with role"""
  username_field = 'email'

  def validate(self, attrs):
    data = super().validate(attrs)
    data['role'] = self.user.role
    return data
  
class RegisterSerializer(serializers.ModelSerializer):
  password = serializers.CharField(write_only=True)

  class Meta:
    model = CustomUser
    fields = ['email', 'password', 'role']

  def create(self, validated_data):
    return CustomUser.objects.create_user(**validated_data)