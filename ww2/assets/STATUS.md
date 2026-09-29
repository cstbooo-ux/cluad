# Asset fetch status (helper session, 2026-09-29 UTC)

**Result: nothing downloaded.** The network policy in this helper container still
denies every host the job needs. The egress proxy answers `CONNECT` with
`403 Forbidden` for each of them. Only the default allowlist got through
(github.com, raw.githubusercontent.com, pypi.org, files.pythonhosted.org, s3.amazonaws.com).
It looks like the widened network policy did not reach this container. It may only
apply to sessions started after the change.

## 1. edge-tts narration: FAILED
- `pip install edge-tts` worked (edge-tts 7.2.8, from PyPI).
- `python3 ww2/tools/tts_gen.py` failed on the first job (`rhineland_0`):
  - host: `speech.platform.bing.com:443`
  - error as-is: `SSLCertVerificationError: certificate verify failed: self-signed certificate in certificate chain`.
    edge-tts pins `certifi.where()`, so it ignores the proxy's CA bundle.
  - Retried with certifi pointed at the environment CA bundle (`/root/.ccr/ca-bundle.crt`):
    `403, message='Invalid response status', url='wss://speech.platform.bing.com/consumer/speech/synthesize/readaloud/edge/v1?...'`
  - `curl https://speech.platform.bing.com/` gives `CONNECT tunnel failed, response 403`
    (the proxy refuses the tunnel).
- Note for later: even after the host is allowed, edge-tts needs the proxy CA. Run it with
  `certifi.where` patched to the CA bundle, or with `SSL_CERT_FILE` plus a small wrapper.
  Do not turn off TLS verification.

## 2. Archival audio: FAILED (no files)
Every source host was refused with `curl: (56) CONNECT tunnel failed, response 403`:
- `commons.wikimedia.org`, `upload.wikimedia.org`, `en.wikipedia.org`
- `archive.org`
- `www.loc.gov`, `tile.loc.gov`, `catalog.archives.gov`
- `www.trumanlibrary.gov`, `www.fdrlibrary.org`, `www.bbc.co.uk`, `freesound.org`

Without those hosts I could not find or check the license of any recording for
fdr_infamy, truman_hiroshima, chamberlain_peace, siren or chamberlain_war. I did not
pull files from unknown GitHub/S3 mirrors, because their license can't be checked.

## 3. Whisper word timestamps: SKIPPED
There was no archival audio to transcribe. Also, the model host `huggingface.co` is
blocked (`CONNECT tunnel failed, response 403`).

## To unblock
In the environment settings (cloud environment menu → Edit → Network access), choose a
broader access level or add these hosts to the allowed domains:
`speech.platform.bing.com`, `commons.wikimedia.org`, `upload.wikimedia.org`,
`archive.org` (plus `*.archive.org` download nodes, e.g. `ia800*.us.archive.org`),
`huggingface.co` and `cdn-lfs.huggingface.co` / `*.hf.co`.
Then rerun this job in a **new** session.
Access levels: https://code.claude.com/docs/en/claude-code-on-the-web
