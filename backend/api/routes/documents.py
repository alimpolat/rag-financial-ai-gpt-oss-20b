"""
Document management endpoints.
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Request
from typing import List
import os
import logging

from services.document_service import DocumentService
from core.config import settings
from core.security import SecurityValidator, validate_upload_file
from core.auth import get_current_user, get_current_user_optional, TokenData, check_rate_limit
from core.dependencies import get_document_service

router = APIRouter()
logger = logging.getLogger("rag_financial_ai")


@router.post("/documents/upload")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    document_service: DocumentService = Depends(get_document_service),
    current_user: TokenData = Depends(get_current_user_optional)  # Made optional for testing
):
    """
    Upload and process a financial document.
    """
    try:
        # Enhanced security validation
        validate_upload_file(file)
        
        # Read file content for additional validation
        content = await file.read()
        
        # Validate file content
        is_valid, error_message = SecurityValidator.validate_file_content(content, file.filename)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_message)
        
        # Sanitize filename
        sanitized_filename = SecurityValidator.sanitize_filename(file.filename)
        
        # Reset file pointer
        await file.seek(0)
        
        logger.info(f"Processing secure document upload: {sanitized_filename}")
        
        # Process document
        result = await document_service.process_document(file)
        
        return {
            "message": "Document uploaded and processed successfully",
            "document_id": result["document_id"],
            "chunks_created": result["chunks_created"],
            "filename": sanitized_filename,
            "security_validated": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        raise HTTPException(status_code=500, detail="Failed to process document")


@router.get("/documents")
async def list_documents(document_service: DocumentService = Depends(get_document_service)):
    """List all uploaded documents."""
    try:
        documents = await document_service.list_documents()
        return {"documents": documents}
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve documents")


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    document_service: DocumentService = Depends(get_document_service)
):
    """Delete a document and its embeddings."""
    try:
        await document_service.delete_document(document_id)
        return {"message": f"Document {document_id} deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete document")


@router.get("/documents/{document_id}/chunks")
async def get_document_chunks(
    document_id: str,
    document_service: DocumentService = Depends(get_document_service)
):
    """Get chunks for a specific document."""
    try:
        chunks = await document_service.get_document_chunks(document_id)
        return {"chunks": chunks}
    except Exception as e:
        logger.error(f"Error retrieving document chunks: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve document chunks")
