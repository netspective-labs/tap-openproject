#!/usr/bin/env python3
"""Test script to verify security fixes in tap-openproject."""

import sys
import json
from pathlib import Path

# Add tap_openproject to path
sys.path.insert(0, str(Path(__file__).parent))

from tap_openproject.tap import TapOpenProject


def test_valid_date_format():
    """Test that valid ISO 8601 dates are accepted."""
    print("\n✓ Testing valid date formats...")
    
    valid_dates = [
        "2024-01-01T00:00:00Z",
        "2024-12-31T23:59:59Z",
        "2024-06-15T12:30:45+00:00",
    ]
    
    for date in valid_dates:
        try:
            from tap_openproject.streams import ProjectsStream
            config = {
                "api_key": "test_key",
                "base_url": "https://test.openproject.org/api/v3",
                "start_date": date
            }
            # Create stream directly and test get_url_params
            stream = ProjectsStream(tap=None, schema=None, name="projects")
            stream.config = config
            params = stream.get_url_params(context=None, next_page_token=None)
            print(f"  ✓ {date} - PASSED")
        except ValueError as e:
            print(f"  ✗ {date} - FAILED: {e}")
            return False
    
    return True


def test_invalid_date_format():
    """Test that invalid dates are rejected."""
    print("\n✓ Testing invalid date formats (should be rejected)...")
    
    invalid_dates = [
        "not-a-date",
        "2024-13-01T00:00:00Z",  # Invalid month
        "'; DROP TABLE projects; --",  # SQL injection attempt
        "../../etc/passwd",  # Path traversal attempt
        "<script>alert('xss')</script>",  # XSS attempt
    ]
    
    for date in invalid_dates:
        try:
            from tap_openproject.streams import ProjectsStream
            config = {
                "api_key": "test_key",
                "base_url": "https://test.openproject.org/api/v3",
                "start_date": date
            }
            # Create stream directly and test get_url_params
            stream = ProjectsStream(tap=None, schema=None, name="projects")
            stream.config = config
            params = stream.get_url_params(context=None, next_page_token=None)
            print(f"  ✗ {date} - FAILED: Should have been rejected!")
            return False
        except ValueError as e:
            print(f"  ✓ {date} - PASSED (rejected as expected)")
    
    return True


def test_error_handling():
    """Test that error handling imports are available."""
    print("\n✓ Testing error handling imports...")
    
    try:
        from tap_openproject.streams import FatalAPIError, RetriableAPIError
        print("  ✓ FatalAPIError imported successfully")
        print("  ✓ RetriableAPIError imported successfully")
        return True
    except ImportError as e:
        print(f"  ✗ Import failed: {e}")
        return False


def test_type_hints():
    """Test that type hints are properly defined."""
    print("\n✓ Testing type hints...")
    
    try:
        from tap_openproject.streams import ProjectsStream, WorkPackagesStream
        import inspect
        
        # Check ProjectsStream.get_url_params return type
        sig = inspect.signature(ProjectsStream.get_url_params)
        return_annotation = sig.return_annotation
        print(f"  ✓ ProjectsStream.get_url_params return type: {return_annotation}")
        
        # Check parse_response return type
        sig = inspect.signature(ProjectsStream.parse_response)
        return_annotation = sig.return_annotation
        print(f"  ✓ ProjectsStream.parse_response return type: {return_annotation}")
        
        return True
    except Exception as e:
        print(f"  ✗ Type hints check failed: {e}")
        return False


def main():
    """Run all security tests."""
    print("=" * 70)
    print("SECURITY FIXES TEST SUITE")
    print("=" * 70)
    
    tests = [
        ("Valid Date Formats", test_valid_date_format),
        ("Invalid Date Formats", test_invalid_date_format),
        ("Error Handling", test_error_handling),
        ("Type Hints", test_type_hints),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ {test_name} - EXCEPTION: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 70)
    print("TEST RESULTS")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{status:12} - {test_name}")
    
    print("=" * 70)
    print(f"OVERALL: {passed}/{total} tests passed")
    print("=" * 70)
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
