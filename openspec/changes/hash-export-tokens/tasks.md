# Tasks

- [x] Add SHA-256 hashing helper for export tokens
- [x] Hash token on create; return plaintext once in creation response
- [x] Stop returning plaintext in token listing
- [x] Add reveal-once endpoint for legacy plaintext tokens
- [x] Hash presented token in feed lookup and RLS context
- [x] Alembic migration: hash existing plaintext rows
- [x] Update SQL RLS policies to compare against hashed token
- [ ] Frontend: show secret once after creation with copy affordance
- [ ] Verify integration tests and CI
