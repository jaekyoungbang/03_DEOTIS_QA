from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from services.document_processor import DocumentProcessor
from models.embeddings import EmbeddingManager
from models.vectorstore import VectorStoreManager
from config import Config
import os
import uuid

document_bp = Blueprint('document', __name__)

# Initialize components
doc_processor = DocumentProcessor()
embedding_manager = EmbeddingManager()
vectorstore_manager = VectorStoreManager(embedding_manager.get_embeddings())

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

@document_bp.route('/upload', methods=['POST'])
def upload_document():
    """Upload and process a document"""
    try:
        # Check if file is in request
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        if not allowed_file(file.filename):
            return jsonify({"error": f"File type not allowed. Allowed types: {Config.ALLOWED_EXTENSIONS}"}), 400
        
        # Save file
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        file_path = os.path.join(Config.UPLOAD_FOLDER, unique_filename)
        file.save(file_path)
        
        # Validate file
        if not doc_processor.validate_file(file_path):
            os.remove(file_path)
            return jsonify({"error": "File validation failed. Check file size and format."}), 400
        
        # Process the document
        metadata = {
            "filename": filename,
            "upload_id": str(uuid.uuid4()),
            "uploaded_at": str(request.headers.get('Date', ''))
        }
        
        chunks = doc_processor.process_file(file_path, metadata)
        
        # Add to vector store
        vectorstore_manager.add_documents(chunks)
        
        return jsonify({
            "message": "Document uploaded and processed successfully",
            "filename": filename,
            "chunks_created": len(chunks),
            "total_documents": vectorstore_manager.get_document_count()
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@document_bp.route('/upload-text', methods=['POST'])
def upload_text():
    """Process raw text input"""
    try:
        data = request.get_json()
        text = data.get('text')
        title = data.get('title', 'Untitled')
        
        if not text:
            return jsonify({"error": "No text provided"}), 400
        
        # Process text
        metadata = {
            "title": title,
            "source": "direct_input",
            "upload_id": str(uuid.uuid4())
        }
        
        chunks = doc_processor.process_text(text, metadata)
        
        # Add to vector store
        vectorstore_manager.add_documents(chunks)
        
        return jsonify({
            "message": "Text processed successfully",
            "title": title,
            "chunks_created": len(chunks),
            "total_documents": vectorstore_manager.get_document_count()
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@document_bp.route('/list', methods=['GET'])
def list_documents():
    """List uploaded documents"""
    try:
        # Get vector DB status
        total_chunks = vectorstore_manager.get_document_count()
        has_documents = total_chunks > 0
        
        # List files in upload folder
        files = []
        if os.path.exists(Config.UPLOAD_FOLDER):
            for filename in os.listdir(Config.UPLOAD_FOLDER):
                file_path = os.path.join(Config.UPLOAD_FOLDER, filename)
                if os.path.isfile(file_path):
                    files.append({
                        "filename": filename,
                        "size": os.path.getsize(file_path),
                        "modified": os.path.getmtime(file_path)
                    })
        
        # Check S3 folder status - Windows compatible path
        import platform
        if platform.system() == "Windows":
            s3_folder = "D:\\99_DEOTIS_QA_SYSTEM\\03_DEOTIS_QA\\s3"
        else:
            s3_folder = "/mnt/d/99_DEOTIS_QA_SYSTEM/03_DEOTIS_QA/s3"
        s3_files = []
        if os.path.exists(s3_folder):
            for filename in os.listdir(s3_folder):
                if filename.endswith(('.pdf', '.docx', '.txt', '.md')):
                    s3_files.append({
                        "filename": filename,
                        "source": "S3"
                    })
        
        return jsonify({
            "files": files,
            "s3_files": s3_files,
            "total_chunks": total_chunks,
            "has_documents": has_documents,
            "status": "loaded" if has_documents else "empty"
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@document_bp.route('/delete/<filename>', methods=['DELETE'])
def delete_document(filename):
    """Delete a document"""
    try:
        # Secure the filename
        filename = secure_filename(filename)
        file_path = os.path.join(Config.UPLOAD_FOLDER, filename)
        
        # Check if file exists
        if not os.path.exists(file_path):
            return jsonify({"error": "File not found"}), 404
        
        # Delete file
        os.remove(file_path)
        
        # Note: Deleting from vector store requires tracking document IDs
        # This is a simplified version
        
        return jsonify({"message": f"Document {filename} deleted successfully"})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@document_bp.route('/load-s3', methods=['POST'])
def load_s3_documents():
    """Load documents from S3 folder"""
    try:
        from load_documents import load_s3_documents
        documents_loaded, total_chunks = load_s3_documents()
        
        # RAG 체인 재초기화 (새로운 문서 인식)
        try:
            import sys
            # 글로벌 RAG 체인 강제 재설정
            if 'app' in sys.modules:
                sys.modules['app'].rag_chain = None
                from app import get_rag_chain
                new_chain = get_rag_chain(force_reload=True)
                print(f"✅ RAG 체인 재초기화 완료 - 문서 수: {new_chain.vectorstore.get_document_count()}")
            else:
                print("⚠️ App 모듈을 찾을 수 없음")
        except Exception as rag_error:
            print(f"⚠️ RAG 체인 재초기화 오류: {rag_error}")
        
        return jsonify({
            "message": "S3 documents loaded successfully",
            "documents_loaded": documents_loaded,
            "total_chunks": total_chunks
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@document_bp.route('/clear-all', methods=['DELETE'])
def clear_all_documents():
    """Clear all documents from vector store"""
    try:
        # Delete all files
        if os.path.exists(Config.UPLOAD_FOLDER):
            for filename in os.listdir(Config.UPLOAD_FOLDER):
                file_path = os.path.join(Config.UPLOAD_FOLDER, filename)
                if os.path.isfile(file_path):
                    os.remove(file_path)
        
        # Clear vector store
        vectorstore_manager.delete_collection()
        
        # Reinitialize vector store
        vectorstore_manager.initialize_vectorstore()
        
        return jsonify({"message": "All documents cleared successfully"})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500