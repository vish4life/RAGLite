from rest_framework import serializers
from .models import Document, Chat

class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at','file_hash','status','page_count','chunk_count']

class ChatSerializer(serializers.ModelSerializer):
    documents = DocumentSerializer(many=True, read_only=True)
    class Meta:
        model = Chat
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

class DocumentUploadSerializer(serializers.Serializer):
    # serializer for document upload
    file = serializers.FileField()

    def validate_file(self, value):
        if not (value.name.endswith('.pdf') or value.name.endswith('.txt')):
            raise serializers.ValidationError("File must be a PDF or TXT")
        return value

        if value.size > 15 * 1024 * 1024:
            raise serializers.ValidationError("File size should be less than 15MB")
        return value
class QuerySerializer(serializers.Serializer):
    # serializer for query requests
    query = serializers.CharField(max_length=1000, required=False)
    question = serializers.CharField(max_length=1000, required=False)
    document_id = serializers.UUIDField(required=False)
    model = serializers.CharField(max_length=50, required=False)

    def validate(self, data):
        if not data.get('query') and not data.get('question'):
            raise serializers.ValidationError("Either 'query' or 'question' must be provided")
        return data
    def validate_query(self, value):
        if not value.strip():
            raise serializers.ValidationError("Query cannot be empty")
        return value
            