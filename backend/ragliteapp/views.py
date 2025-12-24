# ragliteapp/views.py
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from django.core.files.uploadedfile import UploadedFile

import hashlib
import logging
from datetime import datetime

from .models import Document, Chat
from .serializers import DocumentSerializer, ChatSerializer, DocumentUploadSerializer, QuerySerializer
from .llm_services import get_llm_service
from .vectordb_services import get_chroma_service
from .utils import chunk_text_by_size, calculate_hash, extract_text_from_pdf

logger = logging.getLogger(__name__)

class DocumentViewSet(viewsets.ModelViewSet):
    """ ViewSet for document CRUD operations """
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    parser_classes = [MultiPartParser, FormParser]
    
    @action(detail=False, methods=['post'])
    def upload(self, request):
        """
        Upload a PDF document and process it
        POST /ragengine/documents/upload/
        
        Flow:
        1. Validate file upload
        2. Calculate file hash
        3. Check if already exists
        4. Save to database
        5. Extract text from PDF
        6. Chunk text
        7. Store in ChromaDB
        8. Update document status
        """
        # Step 1: Validate file
        serializer = DocumentUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        uploaded_file = serializer.validated_data['file']
        logger.info(f"File uploaded: {uploaded_file}")

        # Step 2: Calculate file hash
        file_hash = calculate_hash(uploaded_file)
        logger.info(f"File hash: {file_hash}")

        # Step 3: Check if document already exists
        existing_doc = Document.objects.filter(file_hash=file_hash).first()
        if existing_doc:
            logger.info(f"Document {file_hash} already exists")
            return Response({"message": "Document already exists"}, status=status.HTTP_200_OK)
        
        # Step 4: Save to database
        document = Document.objects.create(
            name=uploaded_file.name,
            file=uploaded_file,
            file_hash=file_hash,
            status='processing'
        )
        logger.info(f"Document {document.id} created")
        try:
            # Step 5: get file path
            file_path = document.file.path
            logger.info(f"File path: {file_path}")

            # Step 6: Extract text and page countfrom PDF
            full_text, page_count = extract_text_from_pdf(file_path)
            logger.info(f"Extracted {len(full_text)} characters and {page_count} pages from PDF")

            # Step 7: Chunk text
            chunks, metadatas, ids = chunk_text_by_size(file_path, str(document.id))
            logger.info(f"Created {len(chunks)} text chunks")

            # Step 8: Store in ChromaDB
            chroma_service = get_chroma_service()
            chroma_service.add_document_chunks(chunks, metadatas, ids)
            logger.info(f"Stored {len(chunks)} text chunks in ChromaDB")
            
            # Step 9: Update document status
            document.status = 'completed'
            document.page_count = page_count
            document.chunk_count = len(chunks)
            document.save()
            logger.info(f"Document {document.id} completed")

            return Response(
                {
                    'message': 'Document uploaded and processed successfully',
                    'document': DocumentSerializer(document).data,
                    'processing': {
                        'pages': page_count,
                        'chunks': len(chunks),
                        'characters': len(full_text)
                    }
                },
                status=status.HTTP_200_OK
            )
        except Exception as e:
            logger.error(f"Error processing document: {str(e)}")
            document.status = 'failed'
            document.save()
            return Response(
                {
                    'message': 'Document uploaded but processing failed',
                    'error': str(e),
                    'document': DocumentSerializer(document).data
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
class ChatViewSet(viewsets.ModelViewSet):
    """ ViewSet for chat history """
    queryset = Chat.objects.all()
    serializer_class = ChatSerializer

    @action(detail=False, methods=['post'])
    def query(self, request):
        """
        Query the RAG system
        POST /ragengine/chats/query/
        
        Flow:
        1. Validate question
        2. Check for exact match in SQLite
        3. Check for similar question in ChromaDB
        4. If not cached, search documents
        5. Generate answer with LLM
        6. Save to SQLite and ChromaDB
        7. Return answer
        """
        logger.info(f"Query: {request.data}")
        # Step 1: Validate query
        serializer = QuerySerializer(data=request.data)
        if not serializer.is_valid():
            logger.info(f"Serializer is not valid: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        query = serializer.validated_data.get('query') or serializer.validated_data.get('question')
        document_id = serializer.validated_data.get('document_id')
        model = serializer.validated_data.get('model')
        
        # Step 2: Check for exact match in SQLite
        exact_match = Chat.objects.filter(question__iexact=query).first()
        if exact_match:
            logger.info(f"Exact match found for query: {query}")
            return Response({
                'answer': exact_match.answer,
                'source': 'cache match',
                'chat_id': exact_match.id,
                'source_chunks': exact_match.source_chunks_metadata,
            }, status=status.HTTP_200_OK)
        
        # Step 3: Check for similar question in ChromaDB
        chroma_service = get_chroma_service()
        similar_questions = chroma_service.find_similar_question(query)
        if similar_questions:
            chat_id, distance = similar_questions
            logger.info(f"Similar question found (distance: {distance:.4f})")
            try:
                cached_chat = Chat.objects.get(id=chat_id)
                logger.info(f"Cached chat found for query: {query}")
                return Response({
                    'answer': cached_chat.answer,
                    'source': 'cache similar',
                    'chat_id': cached_chat.id,
                    'source_chunks': cached_chat.source_chunks_metadata,
                    'similarity_score': 1- distance # convert distance to similarity score
                }, status=status.HTTP_200_OK)
            except Chat.DoesNotExist:
                logger.info(f"Cached chat not found for query: {query}")
            
        # Step 4: No cache hit - search documents
        logger.info("No cache hit - searching documents")
        
        try:
            # Search ChromaDB for relevant chunks
            search_results = chroma_service.search_document_chunks(
                query,
                k=3,
                document_id=document_id if document_id else None
            )
            if not search_results['documents'][0]:
                return Response(
                    {'message': 'No relevant documents found. Please upload documents first.'},
                    status=status.HTTP_404_NOT_FOUND
                )
            # build context from retrieved chunks
            chunks = search_results['documents'][0]
            metadatas = search_results['metadatas'][0]
            ids = search_results['ids'][0]
            context = "\n\n---\n\n".join(chunks)
            logger.info(f"Retrieved {len(chunks)} chunks from ChromaDB")

            # Step 5: Generate answer with LLM
            llm_service = get_llm_service()
            answer = llm_service.generate_answer(
                query,
                context,
                model_name=model if model else 'llama3.2'          
            )
            if not answer:
                return Response(
                    {'message': 'Failed to generate answer. Please try again.'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            logger.info(f"Generated answer ({len(answer)} characters)")

            # Step 6: Save to SQLite
            chat = Chat.objects.create(
                question=query,
                answer=answer,
                model=model if model else 'llama3.2',
                source_chunks_metadata=metadatas,
                similarity_score=None # new question so no similarity score
            )
            # Associate with documents if specific document was queried
            if document_id:
                try:
                    from .models import Document
                    doc = Document.objects.get(id=document_id)
                    chat.documents.add(doc)
                except Document.DoesNotExist:
                    pass
            # Step 7: Cache question in ChromaDB
            chroma_service = get_chroma_service()
            chroma_service.add_cached_question(query, str(chat.id), answer)
            logger.info("Cached question in ChromaDB")
            
            # Step 8: Return answer
            return Response({
                'answer': answer,
                'source': 'generated',
                'chat_id': chat.id,
                'source_chunks': metadatas,
                'chunks_used': len(chunks)
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            return Response(
                {'message': 'Failed to process query. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    @action(detail=False, methods=['post'])
    def testinput(self, request):
        """
        Test input for query
        POST /ragengine/chats/testinput/
        """
        print('came into testinput')
        serializer = QuerySerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        query = serializer.validated_data['query']
        document_id = serializer.validated_data.get('document_id')
        model = serializer.validated_data.get('model')
        logger.info(f"Test input successful for query: {query} document_id: {document_id} model: {model}")
        return Response({
            'answer': 'Test input successful',
            'request': request.data
        }, status=status.HTTP_200_OK)
            