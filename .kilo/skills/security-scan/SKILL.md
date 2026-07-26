---
name: security-scan
description: PII/secret/threat scanning procedures. API key detection, network anomaly checks, suspicious file identification.
---

# Security Scan

## When to Use
- Scanning repos for accidentally committed secrets
- Checking for PII in tracked files
- Auditing network connections for anomalies
- Identifying suspicious executables or files

## File Scanning
```
# Patterns to detect
API_KEY, SECRET_KEY, PRIVATE_KEY, PASSWORD
Bearer tokens, JWT tokens
AWS credentials (AKIA...)
SSH private keys (-----BEGIN)
.env files in tracked paths
```

## Network Scanning (lightweight)
- `netstat -an` for active connections
- Check for unexpected listening ports
- Flag connections to known-bad IP ranges
- Audit Bluetooth paired devices

## Report Format
| Severity | Finding | Location | Recommendation |
|----------|---------|----------|----------------|
| CRITICAL | Exposed API key | file:line | Rotate immediately |
| HIGH | .env in git | .env | Add to .gitignore |

## Rules
- Never display actual secret values
- Read-only operations only
- Use gitleaks config (`.gitleaks.toml`) when available
