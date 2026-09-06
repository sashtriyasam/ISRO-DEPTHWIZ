# Windows Code Signing Preparation

**DepthWizard — SIH 26175**  
**Document Version:** 1.0  
**Date:** 2026-09-06

---

## Current Status

**Code Signing:** ❌ **NOT CONFIGURED** — Unsigned test/development build only

**Evidence:**

- `electron-builder.yml`: `forceCodeSigning: false`, `signAndEditExecutable: false`
- Installer built with `npm run electron:build:win` produces unsigned artifacts
- No certificate configured in environment or repository

---

## Required Certificate

### Certificate Type

- **Code Signing Certificate (EV preferred)** — Extended Validation certificate from a trusted CA (DigiCert, Sectigo, GlobalSign, etc.)
- Must support Microsoft Authenticode signing
- Must support timestamping (RFC 3161)

### Certificate Requirements

| Property               | Requirement                                     |
| ---------------------- | ----------------------------------------------- |
| **Key Usage**          | Code Signing (1.3.6.1.5.5.7.3.3)                |
| **Extended Key Usage** | Microsoft Authenticode (1.3.6.1.4.1.311.10.3.1) |
| **Key Size**           | ≥ 2048-bit RSA (3072/4096 preferred)            |
| **Validity**           | ≥ 1 year (3 years typical for EV)               |
| **Timestamping**       | RFC 3161 compatible TSA URL                     |

### Supported Formats

- PFX/P12 (PKCS#12) — preferred for CI
- PEM + private key (separate files)

---

## Environment Variables / Secrets Required

### Required Secrets (GitHub Actions / CI)

| Secret Name                  | Description                    | Example Value                   |
| ---------------------------- | ------------------------------ | ------------------------------- |
| `WINDOWS_CODE_SIGN_CERT`     | Base64-encoded PFX certificate | `MIIK...`                       |
| `WINDOWS_CODE_SIGN_PASSWORD` | PFX password                   | `cert-password-123`             |
| `WINDOWS_CODE_SIGN_TSA_URL`  | Timestamp Authority URL        | `http://timestamp.digicert.com` |

### Optional: EV Certificate Additional

| Secret Name               | Description                             |
| ------------------------- | --------------------------------------- |
| `WINDOWS_EV_CERT_SUBJECT` | Certificate subject DN for verification |

### Local Development (Manual Signing)

```bash
# Set in environment before building
export WINDOWS_CODE_SIGN_CERT="base64-cert..."
export WINDOWS_CODE_SIGN_PASSWORD="cert-password"
export WINDOWS_CODE_SIGN_TSA_URL="http://timestamp.digicert.com"
```

---

## Electron Builder Configuration Updates

### Current `electron-builder.yml` (Unsigned)

```yaml
win:
  target:
    - target: nsis
      arch:
        - x64
  forceCodeSigning: false
  signAndEditExecutable: false
```

### Required Updates for Signed Builds

```yaml
win:
  target:
    - target: nsis
      arch:
        - x64
  forceCodeSigning: true # Fail build if signing fails
  signAndEditExecutable: true # Sign executables
  certificateFile: "" # Path set via env var
  certificatePassword: "" # Password via env var
  rfc3161TimeStampServer: "" # TSA URL via env var
```

### Environment Variable Mapping (electron-builder)

| electron-builder Config  | Environment Variable    |
| ------------------------ | ----------------------- |
| `certificateFile`        | `CSC_LINK` (base64 PFX) |
| `certificatePassword`    | `CSC_KEY_PASSWORD`      |
| `rfc3161TimeStampServer` | `CSC_TIMESTAMP_SERVER`  |

---

## CI Integration (GitHub Actions)

### Required Workflow Updates

```yaml
# In .github/workflows/ci.yml — add to electron-build job
env:
  CSC_LINK: ${{ secrets.WINDOWS_CODE_SIGN_CERT }}
  CSC_KEY_PASSWORD: ${{ secrets.WINDOWS_CODE_SIGN_PASSWORD }}
  CSC_TIMESTAMP_SERVER: ${{ secrets.WINDOWS_CODE_SIGN_TSA_URL }}
```

### Required GitHub Secrets

Navigate to: `Settings → Secrets and variables → Actions → New repository secret`

| Secret                       | Value Source            |
| ---------------------------- | ----------------------- |
| `WINDOWS_CODE_SIGN_CERT`     | Base64 PFX from CA      |
| `WINDOWS_CODE_SIGN_PASSWORD` | Certificate password    |
| `WINDOWS_CODE_SIGN_TSA_URL`  | CA timestamp server URL |

---

## Build Commands

### Local Signed Build

```bash
# Set environment variables first
export CSC_LINK="$(base64 -w0 cert.pfx)"
export CSC_KEY_PASSWORD="cert-password"
export CSC_TIMESTAMP_SERVER="http://timestamp.digicert.com"

npm run electron:build:win
```

### CI Signed Build (GitHub Actions)

```yaml
- name: Build signed Windows installer
  run: npm run electron:build:win
  env:
    CSC_LINK: ${{ secrets.WINDOWS_CODE_SIGN_CERT }}
    CSC_KEY_PASSWORD: ${{ secrets.WINDOWS_CODE_SIGN_PASSWORD }}
    CSC_TIMESTAMP_SERVER: ${{ secrets.WINDOWS_CODE_SIGN_TSA_URL }}
```

---

## Artifact Verification

### Verify Signature (Post-Build)

```powershell
# Verify installer signature
Get-AuthenticodeSignature "release/DepthWizard Setup 0.1.0.exe" | Format-List

# Verify executable signature
Get-AuthenticodeSignature "release/win-unpacked/DepthWizard.exe" | Format-List

# Expected output:
# SignerCertificate: [Valid CA certificate]
# Status: Valid
# StatusMessage: "The signature is valid"
```

### Verify Timestamp

```powershell
$sig = Get-AuthenticodeSignature "release/DepthWizard Setup 0.1.0.exe"
$sig.TimeStamperCertificate | Format-List
# Should show valid timestamp certificate
```

---

## Certificate Management

### Renewal Timeline

| Event                             | Timeline              |
| --------------------------------- | --------------------- |
| Certificate expiry warning        | 90 days before expiry |
| Renewal initiation                | 60 days before expiry |
| New cert deployed to CI           | 30 days before expiry |
| Old cert revoked (if compromised) | Immediately           |

### Storage & Access

| Principle           | Implementation                          |
| ------------------- | --------------------------------------- |
| **Least privilege** | Only release engineers + CI have access |
| **Secret rotation** | Annual (aligned with cert renewal)      |
| **Audit trail**     | GitHub Actions logs + CA audit logs     |
| **Backup**          | Secure offline backup of PFX + password |

---

## Verification Checklist (Pre-Release)

| Check                                                  | Status |
| ------------------------------------------------------ | ------ |
| Certificate purchased from trusted CA                  | ☐      |
| EV certificate (preferred)                             | ☐      |
| Certificate supports Authenticode                      | ☐      |
| TSA URL provided by CA                                 | ☐      |
| PFX exported with password                             | ☐      |
| Base64 encoded for CI                                  | ☐      |
| Secrets added to GitHub                                | ☐      |
| `forceCodeSigning: true` in config                     | ☐      |
| `signAndEditExecutable: true`                          | ☐      |
| CI secrets configured                                  | ☐      |
| Test signed build locally                              | ☐      |
| Signature verified with `Get-AuthenticodeSignature`    | ☐      |
| Timestamp verified                                     | ☐      |
| Installer installs without "Unknown Publisher" warning | ☐      |

---

## Cost & Procurement

| Item                       | Typical Cost (USD/year) |
| -------------------------- | ----------------------- |
| Standard Code Signing Cert | $200–400                |
| EV Code Signing Cert       | $300–600                |
| Timestamping (included)    | Included                |

**Recommendation:** EV Certificate (required for Windows SmartScreen reputation)

---

## Status

| Item                           | Status    |
| ------------------------------ | --------- |
| Certificate procured           | ❌ NO     |
| CI secrets configured          | ❌ NO     |
| `electron-builder.yml` updated | ❌ NO     |
| CI workflow updated            | ❌ NO     |
| Test signed build              | ☐ PENDING |
| Production signing             | ☐ BLOCKED |

---

**Decision Required:** Obtain EV Code Signing Certificate → Update config → Configure CI → Test → Deploy

**Blocker:** G10 (production) — Code signing required for production distribution
