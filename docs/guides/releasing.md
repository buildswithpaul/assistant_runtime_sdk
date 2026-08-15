# Releasing the SDK to PyPI

How `assistant_runtime_sdk` is published so client machines can
`pip install assistant-runtime-sdk`.

The SDK is the one AR component that ships publicly. It is **AGPL-3.0 and must
stay that way**: FAC is AGPLv3 and imports this package, so a proprietary
dependency would make FAC undistributable under its own licence. Do not
"align" this licence with the proprietary AR apps.

## The one rule

**A version number, once uploaded, is permanent.** You can delete a release
from PyPI, but you can never re-upload that version — `1.0.0` is burned for
good. A mistake means shipping `1.0.1`, not replacing `1.0.0`.

That is why every publish rehearses on TestPyPI first.

## One-time setup

### 1. Accounts

Register at **pypi.org** and, separately, at **test.pypi.org**. They are
independent sites with independent accounts and independent tokens.

**2FA is mandatory on both.** Have an authenticator app ready.

### 2. API tokens

*Account settings → API tokens → Add API token.*

For the **first** upload of a new project the scope must be **"Entire
account"** — project-scoped tokens can only be created once the project
exists. After the first publish, delete that token and create a
project-scoped one for `assistant-runtime-sdk`.

The token is shown **once**. Store it in a password manager. It looks like
`pypi-AgEIcHlwaS5vcmc...`. Repeat on TestPyPI for a second token.

### 3. Credentials file

Create `~/.pypirc`:

```ini
[distutils]
index-servers = pypi testpypi

[pypi]
username = __token__
password = pypi-<your-pypi-token>

[testpypi]
username = __token__
password = pypi-<your-testpypi-token>
```

`username` is the literal string `__token__` — not your account name.

```bash
chmod 600 ~/.pypirc
```

Never commit this file. It is not in the repo and must not be.

### 4. Tooling

```bash
pip install --upgrade build twine
```

## Publishing a release

### 1. Bump the version in two places

Both must match, or the installed package reports a version that does not
exist on PyPI:

- `pyproject.toml` → `version = "X.Y.Z"`
- `assistant_runtime_sdk/__init__.py` → `__version__ = "X.Y.Z"`

### 2. Commit, branch, tag

```bash
git add -u
git commit -m "chore(release): vX.Y.Z"
git push origin develop
git branch -f main develop && git push origin main
git tag -a vX.Y.Z -m "Assistant Runtime SDK vX.Y.Z"
git push origin vX.Y.Z
```

`main` and `develop` are kept at the same commit; `main` is the released
trunk and the tag is what pins the artifact. The GitHub default branch stays
`develop`.

### 3. Build

```bash
rm -rf dist/ build/
python3 -m build
twine check dist/*
```

`build` produces two artifacts, and both are uploaded:

- `assistant_runtime_sdk-X.Y.Z-py3-none-any.whl` — the wheel, what pip prefers
- `assistant_runtime_sdk-X.Y.Z.tar.gz` — the sdist, the source fallback

`twine check` must report `PASSED` for both before going further.

Confirm the metadata is what you expect:

```bash
python3 -c "
import zipfile
z = zipfile.ZipFile('dist/assistant_runtime_sdk-X.Y.Z-py3-none-any.whl')
n = [x for x in z.namelist() if x.endswith('METADATA')][0]
print(z.read(n).decode()[:900])
"
```

Check `Version`, the AGPL classifier, and that `Project-URL` entries point at
`github.com/buildswithpaul/assistant_runtime_sdk`.

### 4. Rehearse on TestPyPI

```bash
twine upload -r testpypi dist/*
```

Verify it installs in a **clean virtualenv**. TestPyPI does not mirror real
dependencies, so point it at PyPI for those:

```bash
python3 -m venv /tmp/sdktest
/tmp/sdktest/bin/pip install \
  -i https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  assistant-runtime-sdk
```

> **Run the import check from a directory that is not the SDK repo.**
> `python -c` puts the current directory first on `sys.path`, so running it
> inside the repo imports the local source tree and the check passes even if
> the upload is broken. Assert on the resolved path:

```bash
cd /tmp && /tmp/sdktest/bin/python -c "
import assistant_runtime_sdk as s
assert 'sdktest' in s.__file__, 'resolved to local source, not the artifact'
from assistant_runtime_sdk.client import get_registration_state
print('OK', s.__version__, s.__file__)
"
```

### 5. Publish

```bash
twine upload dist/*
```

Then confirm against real PyPI with no index overrides:

```bash
python3 -m venv /tmp/sdkprod
/tmp/sdkprod/bin/pip install assistant-runtime-sdk
cd /tmp && /tmp/sdkprod/bin/python -c "
import assistant_runtime_sdk as s
assert 'sdkprod' in s.__file__
print('OK', s.__version__)
"
```

## Naming

PyPI normalises the project name, so:

- **install**: `pip install assistant-runtime-sdk` (hyphens)
- **import**: `import assistant_runtime_sdk` (underscores)

Both spellings resolve on install. Nothing to fix — it just surprises people.

## How consumers depend on it

FAC declares it as an ordinary versioned dependency:

```toml
dependencies = [
    "assistant_runtime_sdk>=1.0.0",
]
```

This replaced a `git+https://...` URL with an embedded GitHub PAT, which
existed only because the SDK repo was private. Publishing to PyPI is what
removed the need for that token. **Never reintroduce a credential-bearing
dependency URL** — if a private install is ever needed again, use an
environment-configured index or an extras group with documented auth.

Note the SDK requires **Python >= 3.10**. Any consumer declaring a lower
`requires-python` floor will fail to resolve.

## Known rough edges

- `pip show` displays an empty `License:` field. The AGPL classifier is
  present and is what tooling reads. The cause is the older
  `license = {text = "AGPL-3.0"}` metadata style; switching to the SPDX form
  `license = "AGPL-3.0-only"` would populate it. Cosmetic.

## Future: Trusted Publishing

The better long-term setup is PyPI **Trusted Publishing**: a GitHub Actions
workflow authenticates via OIDC, so no token is stored anywhere and
`~/.pypirc` becomes unnecessary.

It needs a release workflow the SDK does not have yet. Configure the trusted
publisher on PyPI (*project → Publishing*) against this repo and workflow
file, then publish with `pypa/gh-action-pypi-publish`. Until then, the token
flow above is the supported path.
