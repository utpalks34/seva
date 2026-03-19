# Quick test: Login with your government official account

# Test if government user can login
# This helps debug if there are any password or permission issues

from rest_framework.test import APIClient
from complaints.models import User

client = APIClient()

# Test login with one of the government users
test_users = [
    ('utpal@gmail.com', 'test123'),  # Try their password
    ('admin@govt.com', 'admin@123'),  # Try another
]

for email, password in test_users:
    print(f"\n🔐 Testing login for {email}...")
    response = client.post('/api/govt/login/', {
        'email': email,
        'password': password
    }, format='json')
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.data}")
    
    if response.status_code == 200:
        print(f"✅ Login successful!")
        token = response.data.get('go_token')
        print(f"Token: {token[:20]}...")
        
        # Try to fetch complaints with this token
        client.credentials(HTTP_AUTHORIZATION=f'Token {token}')
        complaints_response = client.get('/api/govt/complaints/')
        print(f"Complaints fetch status: {complaints_response.status_code}")
        if complaints_response.status_code == 200:
            print(f"✅ Can fetch complaints!")
        else:
            print(f"❌ Cannot fetch complaints: {complaints_response.data}")
    else:
        print(f"❌ Login failed")
