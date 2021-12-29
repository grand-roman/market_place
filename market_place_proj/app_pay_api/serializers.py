from rest_framework import serializers


class PaySerialier(serializers.Serializer):
    amount = serializers.FloatField()
    order_id = serializers.IntegerField()
    card = serializers.CharField(max_length=8)
    status = serializers.CharField(max_length=20)
    created_at = serializers.DateTimeField()
    error = serializers.CharField(max_length=255, required=False)
