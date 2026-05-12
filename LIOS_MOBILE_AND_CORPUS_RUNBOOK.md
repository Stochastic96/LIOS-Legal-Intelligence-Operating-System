# LIOS Mobile And Corpus Runbook

## Supported app

- Primary mobile app: `lios-mobile`
- Archived legacy app: `archive/mobile-expo`

Only `lios-mobile` should be used for current development, Expo Go, and user testing.

## Safe cleanup policy

- Do not delete legacy mobile code outright.
- Move retired app code into `archive/` so imports, docs, and history stay recoverable.
- Avoid duplicate startup instructions across old mobile folders.

## Corpus recovery workflow

1. Check whether these files are real data or Git LFS pointers:
   - `data/corpus/legal_chunks.jsonl`
   - `data/corpus/legal_chunks.embeddings.npy`
   - `data/corpus/legal_chunks.faiss`
2. If you see `version https://git-lfs.github.com/spec/v1`, run:

```bash
git lfs pull
```

3. Verify the retriever loads non-zero chunks.
4. Only then trust chat and intelligence corpus-derived behavior.

## Expo Go workflow for `stochastic96`

1. Run `bash start.sh`.
2. Log in to Expo Go using the `stochastic96` account.
3. Scan the QR code while the phone and Mac are on the same Wi-Fi network.
4. In LIOS open `Assistent -> System`.
5. Set:
   - `Server-Adresse` = `http://<mac-lan-ip>:8000`
   - `API-Key` = your `LIOS_API_KEY` value when backend auth is enabled
6. If LAN mode fails, switch Expo to tunnel mode from the Expo terminal.

## Route and auth expectations

- Health: `/health`
- Mobile assistant chat: `/chat`
- Learn endpoints: `/learn/*`
- Intelligence endpoints: `/intelligence/*`
- Upload endpoint: `/api/upload`
- Protected endpoints accept `X-API-Key` when `LIOS_API_KEY` is configured.
