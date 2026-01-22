# JWT Authentication Setup

This guide explains how to configure JWT authentication for the Import/Export Orchestrator service.

## Overview

The service validates JWT tokens to authenticate requests and extract the `client_id` for data isolation. It supports two modes:

1. **JWKS (Asymmetric)** - RS256/ES256 with public keys from a JWKS endpoint (recommended)
2. **Secret Key (Symmetric)** - HS256 with a shared secret

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AUTH_ENABLED` | Yes (prod) | `false` | Enable JWT authentication |
| `JWT_JWKS_URL` | For RS256 | - | JWKS endpoint URL (e.g., `https://your-auth.com/.well-known/jwks.json`) |
| `JWT_ISSUER` | No | - | Expected `iss` claim value |
| `JWT_AUDIENCE` | No | - | Expected `aud` claim value |
| `JWT_CLIENT_ID_CLAIM` | No | `client_id` | JWT claim containing the client ID |
| `JWT_ALGORITHM` | No | `RS256` | Signing algorithm (`RS256`, `ES256`, `HS256`) |
| `JWT_SECRET_KEY` | For HS256 | - | Secret key for symmetric algorithms |
| `JWT_JWKS_CACHE_TTL` | No | `3600` | JWKS cache TTL in seconds |

### Example: Auth0 Configuration

```bash
AUTH_ENABLED=true
JWT_JWKS_URL=https://your-tenant.auth0.com/.well-known/jwks.json
JWT_ISSUER=https://your-tenant.auth0.com/
JWT_AUDIENCE=import-export-api
JWT_CLIENT_ID_CLAIM=org_id
JWT_ALGORITHM=RS256
```

### Example: Okta Configuration

```bash
AUTH_ENABLED=true
JWT_JWKS_URL=https://your-org.okta.com/oauth2/default/v1/keys
JWT_ISSUER=https://your-org.okta.com/oauth2/default
JWT_AUDIENCE=import-export-api
JWT_CLIENT_ID_CLAIM=cid
JWT_ALGORITHM=RS256
```

### Example: Custom Auth with HS256

```bash
AUTH_ENABLED=true
JWT_SECRET_KEY=your-256-bit-secret-key-here
JWT_ISSUER=https://your-auth-service.com
JWT_AUDIENCE=import-export-api
JWT_CLIENT_ID_CLAIM=client_id
JWT_ALGORITHM=HS256
```

## JWT Token Requirements

### Required Claims

| Claim | Description |
|-------|-------------|
| `exp` | Expiration time (required) |
| `iat` | Issued at time (validated) |
| Client ID claim | Must contain a valid UUID (configured via `JWT_CLIENT_ID_CLAIM`) |

### Optional Claims (if configured)

| Claim | Description |
|-------|-------------|
| `iss` | Issuer - validated if `JWT_ISSUER` is set |
| `aud` | Audience - validated if `JWT_AUDIENCE` is set |

### Example Token Payload

```json
{
  "sub": "user-123",
  "client_id": "12345678-1234-1234-1234-123456789abc",
  "iss": "https://your-auth.com/",
  "aud": "import-export-api",
  "exp": 1735689600,
  "iat": 1735686000
}
```

## Client ID Extraction

The service extracts `client_id` from the JWT to isolate data between clients:

1. Looks for the claim specified by `JWT_CLIENT_ID_CLAIM` (default: `client_id`)
2. Falls back to `sub` claim if the configured claim is not found
3. The value must be a valid UUID

### Configuring Custom Claim Names

Different auth providers use different claim names:

| Provider | Claim Name | Configuration |
|----------|------------|---------------|
| Auth0 | `org_id` | `JWT_CLIENT_ID_CLAIM=org_id` |
| Okta | `cid` | `JWT_CLIENT_ID_CLAIM=cid` |
| Custom | `tenant_id` | `JWT_CLIENT_ID_CLAIM=tenant_id` |

## UI Integration

### Microfrontend Mode

When embedded in a host application, provide the token via the config:

```tsx
import { ImportExportProvider } from '@your-org/import-export-ui';

function App() {
  const getToken = () => {
    // Return the JWT from your auth system
    return authService.getAccessToken();
  };

  return (
    <ImportExportProvider
      config={{
        apiBaseUrl: '/api/import-export',
        getAuthToken: getToken,
        onUnauthorized: () => {
          // Handle 401 - redirect to login, refresh token, etc.
          authService.refreshToken();
        }
      }}
    >
      <YourApp />
    </ImportExportProvider>
  );
}
```

### Standalone Mode

For testing, set the token in localStorage:

```javascript
localStorage.setItem('auth_token', 'your-jwt-token-here');
```

## Development Mode

When `AUTH_ENABLED=false` (default for development):

- All requests are allowed without authentication
- A default client ID (`00000000-0000-0000-0000-000000000000`) is used
- Useful for local development and testing

**Warning**: Never deploy to production with `AUTH_ENABLED=false`.

## Troubleshooting

### Token Validation Failed

Check the logs for specific error messages:

| Error | Cause | Solution |
|-------|-------|----------|
| "JWT token has expired" | Token `exp` is in the past | Request a new token |
| "JWT claims verification failed" | Wrong issuer or audience | Check `JWT_ISSUER` and `JWT_AUDIENCE` |
| "No verification key available" | JWKS URL not configured or unreachable | Verify `JWT_JWKS_URL` is correct |
| "No signing key found for kid=..." | Key rotation - old key not in JWKS | Keys are auto-refreshed; wait or check JWKS endpoint |

### JWKS Fetch Errors

If the service can't fetch keys from the JWKS endpoint:

1. Verify the URL is accessible from the service
2. Check network/firewall rules
3. Ensure the JWKS endpoint returns valid JSON with a `keys` array

### Invalid Client ID

If you see "Invalid client_id format in JWT":

1. Ensure the client ID claim contains a valid UUID
2. Check that `JWT_CLIENT_ID_CLAIM` points to the correct claim
3. Verify the JWT payload has the expected structure

## Security Best Practices

1. **Always use HTTPS** for JWKS endpoints
2. **Set issuer and audience** to prevent token misuse
3. **Use RS256** (asymmetric) when possible - no shared secrets
4. **Rotate keys regularly** in your auth provider
5. **Keep token lifetime short** (recommended: 15-60 minutes)
6. **Never log tokens** - they contain sensitive information
