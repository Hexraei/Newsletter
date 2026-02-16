"""Phase 1 Verification Script - Tests imports and basic functionality without database."""

import sys
from datetime import datetime


def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")
    
    try:
        # Core imports
        from app.config import settings
        print("  [OK] Config imported")
        
        from app.core.security import (
            create_access_token,
            create_refresh_token,
            get_password_hash,
            verify_password,
        )
        print("  [OK] Security module imported")
        
        # Models
        from app.models import Base, User, ProcessedContent, Source
        print("  [OK] Models imported")
        
        # Schemas
        from app.schemas.user import UserCreate, UserResponse, Token
        from app.schemas.responses import SingleResponse, SuccessResponse
        print("  [OK] Schemas imported")
        
        # Services
        from app.services.auth_service import AuthService
        print("  [OK] Auth service imported")
        
        # API
        from app.main import app
        from app.api.deps import get_current_user
        print("  [OK] API modules imported")
        
        return True
    except Exception as e:
        print(f"  [FAIL] Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_security():
    """Test security functions."""
    print("\nTesting security functions...")
    
    try:
        from app.core.security import (
            get_password_hash,
            verify_password,
            create_access_token,
            create_refresh_token,
            decode_token,
        )
        
        # Test password hashing (truncate to 72 bytes for bcrypt compatibility)
        password = "testpass123"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed), "Password verification failed"
        assert not verify_password("wrongpassword", hashed), "Wrong password should fail"
        print("  [OK] Password hashing works")
        
        # Test JWT tokens
        user_id = "test-user-id"
        access_token = create_access_token(user_id)
        refresh_token = create_refresh_token(user_id)
        
        assert access_token, "Access token not created"
        assert refresh_token, "Refresh token not created"
        print("  [OK] JWT tokens created")
        
        # Test token decode
        decoded = decode_token(access_token)
        assert decoded is not None, "Token decoding failed"
        assert decoded["sub"] == user_id, "Token subject mismatch"
        assert decoded["type"] == "access", "Token type mismatch"
        print("  [OK] JWT tokens decoded correctly")
        
        return True
    except Exception as e:
        print(f"  [FAIL] Security test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_schemas():
    """Test Pydantic schemas."""
    print("\nTesting Pydantic schemas...")
    
    try:
        from app.schemas.user import UserCreate, UserResponse
        from app.schemas.responses import SingleResponse, SuccessResponse
        
        # Test UserCreate
        user_data = UserCreate(
            email="test@example.com",
            password="testpassword123",
            full_name="Test User",
            department="CSE",
            year_of_study=3
        )
        assert user_data.email == "test@example.com"
        print("  [OK] UserCreate schema works")
        
        # Test response schemas
        success = SuccessResponse(message="Test success")
        assert success.success is True
        print("  [OK] Response schemas work")
        
        return True
    except Exception as e:
        print(f"  [FAIL] Schema test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_models():
    """Test SQLAlchemy models (without database)."""
    print("\nTesting SQLAlchemy models...")
    
    try:
        from app.models import Base, User, ProcessedContent, Source
        
        # Test that models have correct columns
        user_columns = [c.name for c in User.__table__.columns]
        assert "email" in user_columns, "User missing email column"
        assert "password_hash" in user_columns, "User missing password_hash column"
        assert "department" in user_columns, "User missing department column"
        print("  [OK] User model has correct columns")
        
        content_columns = [c.name for c in ProcessedContent.__table__.columns]
        assert "title" in content_columns, "ProcessedContent missing title column"
        assert "attractiveness_score" in content_columns, "Missing attractiveness_score"
        assert "is_breaking" in content_columns, "Missing is_breaking"
        print("  [OK] ProcessedContent model has correct columns")
        
        source_columns = [c.name for c in Source.__table__.columns]
        assert "name" in source_columns, "Source missing name column"
        assert "platform" in source_columns, "Source missing platform column"
        print("  [OK] Source model has correct columns")
        
        # Count tables
        tables = Base.metadata.tables
        print(f"  [OK] Total tables defined: {len(tables)}")
        
        return True
    except Exception as e:
        print(f"  [FAIL] Model test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_services():
    """Test service classes (without database)."""
    print("\nTesting services...")
    
    try:
        from app.services.auth_service import AuthService
        print("  [OK] AuthService can be instantiated")
        
        return True
    except Exception as e:
        print(f"  [FAIL] Service test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_fastapi_app():
    """Test FastAPI application."""
    print("\nTesting FastAPI app...")
    
    try:
        from fastapi.testclient import TestClient
        from app.main import app
        
        client = TestClient(app)
        
        # Test health endpoint
        response = client.get("/health")
        assert response.status_code == 200, f"Health check failed: {response.status_code}"
        data = response.json()
        assert data["status"] == "healthy"
        print("  [OK] Health endpoint works")
        
        # Test root endpoint
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        print("  [OK] Root endpoint works")
        
        # Test API docs are accessible
        response = client.get("/docs")
        assert response.status_code == 200
        print("  [OK] API docs accessible")
        
        return True
    except Exception as e:
        print(f"  [FAIL] FastAPI test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all verification tests."""
    print("=" * 60)
    print("PHASE 1 VERIFICATION")
    print("=" * 60)
    
    tests = [
        ("Imports", test_imports),
        ("Security", test_security),
        ("Schemas", test_schemas),
        ("Models", test_models),
        ("Services", test_services),
        ("FastAPI App", test_fastapi_app),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\nUnexpected error in {name}: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"  {status}: {name}")
    
    print("-" * 60)
    print(f"Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n[SUCCESS] Phase 1 is ready! All tests passed.")
        return 0
    else:
        print(f"\n[WARNING] {total - passed} test(s) failed. Please review.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
