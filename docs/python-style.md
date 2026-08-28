# Python style
Use type hints, small functions, and explicit error handling.
```python
def retry(operation, attempts=3):
    for _ in range(attempts):
        try: return operation()
        except Exception: pass
    raise RuntimeError("operation failed")
```
