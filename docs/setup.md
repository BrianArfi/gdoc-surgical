# Setup, auth and requirements

[Back to README](../README.md)

## Full setup

**1. Get the code and install the two Google libraries.**

```bash
git clone https://github.com/BrianArfi/gdoc-surgical
cd gdoc-surgical
pip install -r requirements.txt
```

**2. Create an OAuth client.** In the Google Cloud Console, open **APIs and Services, Credentials, Create credentials, OAuth client ID, Desktop app**, and download the JSON as `client_secret.json`. Enable the **Google Docs API** and the **Google Drive API** on the same project.

**3. Sign in once.** A browser opens for the Google sign-in.

```bash
python3 gdoc_surgical.py auth --credentials client_secret.json
```

**4. Read a document.** The document id is the long string in the doc URL, between `/d/` and `/edit`.

```bash
python3 gdoc_surgical.py read --id DOC_ID
```

**5. Make one edit.**

```bash
python3 gdoc_surgical.py replace --id DOC_ID --find "Q3 target" --with "Q4 target"
```

### Try it first

No Google account and no network needed:

```bash
python3 tests/test_gdoc_surgical.py
python3 gdoc_surgical.py --version
```

The tests run the request builders and the guards against a fake document. For a first real edit, make a copy of a document (**File, Make a copy**) and point the commands at the copy.

## Auth

The token lands in `~/.config/gdoc-surgical/default.json` and refreshes itself. The token file is written with owner-only permissions where the OS supports it.

- **Several accounts:** `--account work` writes and reads `work.json`. Every command takes the same flag.
- **A token file elsewhere:** `--token /path/to/token.json` overrides `--account`. The `GDOC_SURGICAL_TOKEN` environment variable does the same.
- **A different config folder:** set `GDOC_SURGICAL_HOME`.
- **A token from another tool:** a Drive-scoped token issued by another tool works here. The Docs API accepts it.

The sign-in asks for the Google Drive scope (`https://www.googleapis.com/auth/drive`), so the token can edit any document your account can edit.

**Timeout.** On macOS and Linux, a run stops after 180 seconds so it cannot hang on the API. Change it with `GDOC_SURGICAL_TIMEOUT` (seconds). The timeout uses a Unix signal, so it does not apply on Windows.

## Use it as an agent skill

`SKILL.md` carries the rules of engagement in the format that Claude Code and similar harnesses read. Copy the directory into your skills folder:

```bash
cp -r gdoc-surgical ~/.claude/skills/
```

The rule that matters for an agent: read the live document before writing to it. A version number or a changelog row is not a substitute, because somebody can edit a document without touching either.

## Tests

```bash
python3 tests/test_gdoc_surgical.py
```

No network and no credentials. The request builders and the guards are pure functions over plain dicts, so a fake document stands in for a real one.

## Requirements

- **Python 3** with `pip`.
- **Two libraries:** `google-api-python-client` 2.0 or later and `google-auth-oauthlib` 1.0 or later, from `requirements.txt`.
- **A Google Cloud project** with the Google Docs API and the Google Drive API enabled, and an OAuth client of type Desktop app.
- **Edit access** to the document you want to change.
- **Optional:** Claude Code or a similar AI agent, to drive the commands from plain-language requests.
