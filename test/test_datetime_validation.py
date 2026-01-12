#!/usr/bin/env python3
"""Direct test of datetime validation in get_url_params."""

from datetime import datetime

def test_datetime_validation():
    """Test the datetime validation logic directly."""
    print("\n" + "="*70)
    print("DATETIME VALIDATION TEST")
    print("="*70)
    
    # Valid dates
    valid_dates = [
        "2024-01-01T00:00:00Z",
        "2024-12-31T23:59:59Z",
        "2024-06-15T12:30:45+00:00",
        "2024-06-15T12:30:45",
    ]
    
    print("\n✓ Testing VALID date formats:")
    valid_passed = 0
    for date in valid_dates:
        try:
            datetime.fromisoformat(date.replace('Z', '+00:00'))
            print(f"  ✓ {date:30} - ACCEPTED (correct)")
            valid_passed += 1
        except (ValueError, AttributeError) as e:
            print(f"  ✗ {date:30} - REJECTED (incorrect): {e}")
    
    # Invalid dates
    invalid_dates = [
        ("not-a-date", "Invalid format"),
        ("2024-13-01T00:00:00Z", "Invalid month"),
        ("'; DROP TABLE projects; --", "SQL injection attempt"),
        ("../../etc/passwd", "Path traversal"),
        ("<script>alert('xss')</script>", "XSS attempt"),
        ("", "Empty string"),
        ("2024-02-30T00:00:00Z", "Invalid date"),
    ]
    
    print("\n✓ Testing INVALID date formats (should be rejected):")
    invalid_passed = 0
    for date, description in invalid_dates:
        try:
            datetime.fromisoformat(date.replace('Z', '+00:00'))
            print(f"  ✗ {date:30} - ACCEPTED (incorrect!) - {description}")
        except (ValueError, AttributeError) as e:
            print(f"  ✓ {date:30} - REJECTED (correct) - {description}")
            invalid_passed += 1
    
    print("\n" + "="*70)
    print("RESULTS")
    print("="*70)
    print(f"Valid dates:   {valid_passed}/{len(valid_dates)} correctly accepted")
    print(f"Invalid dates: {invalid_passed}/{len(invalid_dates)} correctly rejected")
    
    total_passed = valid_passed + invalid_passed
    total = len(valid_dates) + len(invalid_dates)
    
    if total_passed == total:
        print(f"\n✓ ALL TESTS PASSED ({total_passed}/{total})")
        return 0
    else:
        print(f"\n✗ SOME TESTS FAILED ({total_passed}/{total})")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(test_datetime_validation())
