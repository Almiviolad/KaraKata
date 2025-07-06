from rest_framework import serializers
from .models import ShippingAddress

class ShippingSerializer(serializers.ModelSerializer):

    class meta:
        model = ShippingAddress
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'user']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)