import jwt
import datetime

# Generate token
token = jwt.encode(
    {
        'customer_id': 'test123',
        'exp': (datetime.datetime.utcnow() + datetime.timedelta(days=7)).timestamp()
    },
    '3THyJasmgCZoguT7xwoiaYI4r27fSixi',
    algorithm='HS256'
)

# Create authorization header
auth_header = f'Bearer {token}'

# Save to file
with open('../auth_token.txt', 'w') as f:
    f.write(auth_header)

print('Token saved to auth_token.txt:')
print(auth_header) 