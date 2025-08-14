from flask import Blueprint, request, jsonify, stream_with_context, Response
from services.rag_chain import RAGChain
import json

chat_bp = Blueprint('chat', __name__)

# Initialize RAG chain (consider using app context or dependency injection in production)
rag_chain = None

def get_rag_chain():
    global rag_chain
    if rag_chain is None:
        rag_chain = RAGChain()
    return rag_chain

@chat_bp.route('/query', methods=['POST'])
@chat_bp.route('/../rag/chat', methods=['POST'])
def query():
    """Handle chat queries"""
    try:
        data = request.get_json()
        question = data.get('question')
        use_memory = data.get('use_memory', False)
        
        if not question:
            return jsonify({"error": "Question is required"}), 400
        
        # Get RAG chain instance
        chain = get_rag_chain()
        
        # Query the RAG system
        response = chain.query(question, use_memory=use_memory)
        
        return jsonify(response)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@chat_bp.route('/stream', methods=['POST'])
def stream_query():
    """Handle streaming chat queries"""
    try:
        data = request.get_json()
        question = data.get('question')
        
        if not question:
            return jsonify({"error": "Question is required"}), 400
        
        def generate():
            chain = get_rag_chain()
            # For streaming, we need to modify the chain to support streaming
            # This is a simplified version
            response = chain.query(question)
            
            # Stream the response in chunks
            answer = response.get('answer', '')
            for char in answer:
                yield f"data: {json.dumps({'token': char})}\n\n"
            
            # Send source documents at the end
            yield f"data: {json.dumps({'sources': response.get('source_documents', [])})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
        
        return Response(
            stream_with_context(generate()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no'
            }
        )
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@chat_bp.route('/clear-memory', methods=['POST'])
def clear_memory():
    """Clear conversation memory"""
    try:
        chain = get_rag_chain()
        chain.clear_memory()
        return jsonify({"message": "Memory cleared successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500