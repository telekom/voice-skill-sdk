# Skill manifest

Every skill has a manifest which states what configuration the skills needs and which tokens the skill should get on an invoke.

## Tokens in the skill manifest

The CVI core supports multiple token types (OAuth2, via IDM exchanged tokens, …​). The following sections list these token types and show example JSON.

### OAUTH2_AUTHORIZATION_CODE

Example:
```json
{
  "id": "tokenId",
  "parameter": {
    "type": "OAUTH2_AUTHORIZATION_CODE",
    "authorizationUrl": "authorizationUrl",
    "tokenUrl": "tokenUrl",
    "scopes": [
      "scope-1",
      "scope-2"
    ],
    "clientId": "clientId",
    "clientSecret": "clientSecret"
  }
}
```

### OAUTH2_AUTHORIZATION_CODE_SERVER

Example:
```json
{
  "id": "tokenId",
  "parameter": {
    "type": "OAUTH2_AUTHORIZATION_CODE_SERVER",
    "authorizationUrl": "authorizationUrl",
    "tokenUrl": "tokenUrl",
    "scopes": [
      "scope-1",
      "scope-2"
    ],
    "clientId": "clientId",
    "clientSecret": "clientSecret",
    "redirectUri": "redirectUri"
  }
}
```

### OAUTH2_IMPLICIT

Example:
```json
{
  "id": "tokenId",
  "parameter": {
    "type": "OAUTH2_IMPLICIT",
    "authorizationUrl": "authorizationUrl",
    "scopes": [
      "scope"
    ],
    "clientId": "clientId"
  }
}
```

### OAUTH2_PASSWORD_CREDENTIALS

Example:
```json
{
  "id": "tokenId",
  "parameter": {
    "type": "OAUTH2_PASSWORD_CREDENTIALS",
    "tokenUrl": "tokenUrl",
    "scopes": [
      "scope"
    ],
    "clientId": "clientId"
  }
}
```

### CVI

Example:
```json
{
  "id": "tokenId",
  "parameter": {
    "type": "CVI"
  }
}
```

### EXTERNAL_SERVICE

Example:
```json
{
  "id": "tokenId",
  "parameter": {
    "type": "EXTERNAL_SERVICE"
  }
}
```

### IDM_EXCHANGE

Example:
```json
{
  "id": "tokenId",
  "parameter": {
    "type": "IDM_EXCHANGE",
    "scopes": [
      "scope-1",
      "scope-2"
    ]
  }
}
```
