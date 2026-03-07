"""
NyayaGPT Lite - Backend API Tests
Run with: pytest tests/test_api.py -v
"""

import pytest
from fastapi.testclient import TestClient
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import app

client = TestClient(app)


class TestHealthEndpoints:
    """Test health check endpoints"""
    
    def test_root_endpoint(self):
        """Test root endpoint returns health status"""
        response = client.get("/")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
        assert "timestamp" in response.json()
    
    def test_health_endpoint(self):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


class TestDocumentExplanation:
    """Test document explanation endpoints"""
    
    def test_explain_document_english(self):
        """Test explaining document in English"""
        document_text = """
        FIRST INFORMATION REPORT
        FIR No: 123/2024
        Complainant: John Doe
        Accused: Jane Smith
        Sections: IPC 420
        """
        
        response = client.post(
            "/api/explain-document",
            json={
                "text": document_text,
                "language": "english"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check all required fields are present
        assert "summary" in data
        assert "parties" in data
        assert "stage" in data
        assert "nextSteps" in data
        assert "options" in data
        assert "documentType" in data
    
    def test_explain_document_hindi(self):
        """Test explaining document in Hindi"""
        document_text = """
        प्रथम सूचना रिपोर्ट
        FIR संख्या: 123/2024
        शिकायतकर्ता: राम कुमार
        """
        
        response = client.post(
            "/api/explain-document",
            json={
                "text": document_text,
                "language": "hindi"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify Hindi content
        assert "summary" in data
        assert len(data["summary"]) > 0
    
    def test_explain_document_too_short(self):
        """Test that short documents are rejected"""
        response = client.post(
            "/api/explain-document",
            json={
                "text": "Short text",
                "language": "english"
            }
        )
        
        assert response.status_code == 400
        assert "too short" in response.json()["detail"].lower()
    
    def test_explain_document_missing_text(self):
        """Test that missing text field is handled"""
        response = client.post(
            "/api/explain-document",
            json={
                "language": "english"
            }
        )
        
        assert response.status_code == 422  # Validation error


class TestDocumentTypes:
    """Test document type detection and handling"""
    
    def test_fir_detection(self):
        """Test FIR document type detection"""
        fir_text = """
        FIRST INFORMATION REPORT
        Police Station: Test Station
        FIR No: 001/2024
        """
        
        response = client.post(
            "/api/explain-document",
            json={"text": fir_text, "language": "english"}
        )
        
        assert response.status_code == 200
        assert response.json()["documentType"] == "FIR"
    
    def test_court_order_detection(self):
        """Test court order document type detection"""
        court_order_text = """
        IN THE HIGH COURT
        COURT ORDER
        Case No: 123/2024
        """
        
        response = client.post(
            "/api/explain-document",
            json={"text": court_order_text, "language": "english"}
        )
        
        assert response.status_code == 200
        assert response.json()["documentType"] == "COURT_ORDER"
    
    def test_legal_notice_detection(self):
        """Test legal notice document type detection"""
        notice_text = """
        LEGAL NOTICE
        To: John Doe
        Subject: Payment demand
        """
        
        response = client.post(
            "/api/explain-document",
            json={"text": notice_text, "language": "english"}
        )
        
        assert response.status_code == 200
        assert response.json()["documentType"] == "LEGAL_NOTICE"


class TestUtilityEndpoints:
    """Test utility endpoints"""
    
    def test_get_document_types(self):
        """Test document types endpoint"""
        response = client.get("/api/document-types")
        
        assert response.status_code == 200
        data = response.json()
        assert "documentTypes" in data
        assert len(data["documentTypes"]) > 0
        
        # Check structure of first document type
        doc_type = data["documentTypes"][0]
        assert "type" in doc_type
        assert "name" in doc_type
        assert "description" in doc_type
    
    def test_get_languages(self):
        """Test supported languages endpoint"""
        response = client.get("/api/languages")
        
        assert response.status_code == 200
        data = response.json()
        assert "languages" in data
        
        # Check for English and Hindi
        languages = data["languages"]
        codes = [lang["code"] for lang in languages]
        assert "english" in codes
        assert "hindi" in codes


class TestErrorHandling:
    """Test error handling"""
    
    def test_invalid_language(self):
        """Test handling of invalid language"""
        response = client.post(
            "/api/explain-document",
            json={
                "text": "A" * 100,  # Long enough text
                "language": "invalid_language"
            }
        )
        
        # Should still work but default to English
        assert response.status_code == 200
    
    def test_malformed_json(self):
        """Test handling of malformed JSON"""
        response = client.post(
            "/api/explain-document",
            data="not json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422


# Run tests with: pytest tests/test_api.py -v
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
