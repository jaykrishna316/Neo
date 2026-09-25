#!/usr/bin/env python3
"""
Shared test file - Dev1 and Dev2 both want to edit this

This file will be edited by both developers to demonstrate
the lock mechanism preventing concurrent edits.
"""


def calculate_total(items):
    """Calculate sum of items"""
    return sum(items)


def validate_input(data):
    """Validate input data"""
    if not data:
        return False
    return len(data) > 0


def process_data(data):
    """Process the data"""
    total = calculate_total(data)
    is_valid = validate_input(data)

    if is_valid:
        return {"total": total, "valid": True}
    else:
        return {"total": 0, "valid": False}


if __name__ == "__main__":
    sample_data = [1, 2, 3, 4, 5]
    result = process_data(sample_data)
    print(f"Result: {result}")
