from django.urls import path,include
from rest_framework import routers
from .views import DocumentViewSet, ChatViewSet

router = routers.DefaultRouter()
router.register(r'documents', DocumentViewSet,basename='documents')
router.register(r'chats', ChatViewSet,basename='chats')

urlpatterns = [
    path('', include(router.urls)),
]