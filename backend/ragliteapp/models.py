from django.db import models
import uuid

# ===== MODEL FOR STORING & TRACKING DOCUMENTS =====
class Document(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    file = models.FileField(upload_to='documents/')
    file_hash = models.CharField(max_length=32,unique=True) # MD5 hash of the file
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # Meta data for the document
    page_count = models.IntegerField(null=True, blank=True)
    chunk_count = models.IntegerField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name

# ===== MODEL FOR TRACKING AND STORING CHAT CONVERSATIONS =====
class Chat(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # question and answer
    question = models.TextField()
    answer = models.TextField()
    
    # document reference
    documents = models.ManyToManyField(Document,related_name='chats')
    
    # metadata for debugging
    source_chunks_metadata = models.JSONField(null=True, blank=True)
    similarity_score = models.FloatField(null=True, blank=True)
    model = models.CharField(max_length=20, null=True, blank=True)
    
    # timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.question[:50]}..."
