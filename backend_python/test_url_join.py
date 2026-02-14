#!/usr/bin/env python3
"""
Test URL joining behavior for Doubao API
"""

from urllib.parse import urljoin

# Test the URL joining behavior
base_url = "https://ark.cn-beijing.volces.com/api/v3"
endpoint = "/chat/completions"

full_url = urljoin(base_url, endpoint)
print(f"Base URL: {base_url}")
print(f"Endpoint: {endpoint}")
print(f"Full URL: {full_url}")

# Expected: https://ark.cn-beijing.volces.com/api/v3/chat/completions
# Actual: https://ark.cn-beijing.volces.com/chat/completions (incorrect)

# To fix this, we need to ensure the base URL ends with a slash
base_url_with_slash = "https://ark.cn-beijing.volces.com/api/v3/"
full_url_fixed = urljoin(base_url_with_slash, endpoint)
print(f"\nWith trailing slash:")
print(f"Base URL: {base_url_with_slash}")
print(f"Full URL: {full_url_fixed}")

# Alternative approach - include v3 in the endpoint
base_url_simple = "https://ark.cn-beijing.volces.com"
endpoint_with_version = "/api/v3/chat/completions"
full_url_alt = urljoin(base_url_simple, endpoint_with_version)
print(f"\nAlternative approach:")
print(f"Base URL: {base_url_simple}")
print(f"Endpoint: {endpoint_with_version}")
print(f"Full URL: {full_url_alt}")