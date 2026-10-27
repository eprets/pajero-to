import json
import base64
import requests
import streamlit as st

FILE_PATH = "data.json"


def _get_secrets():
    try:
        token = st.secrets.get("GITHUB_TOKEN", "")
        repo = st.secrets.get("GITHUB_REPO", "")
        return token, repo
    except Exception:
        # Локальный запуск без secrets.toml
        return "", ""


def _api_url(repo):
    return f"https://api.github.com/repos/{repo}/contents/{FILE_PATH}"


def load_data():
    token, repo = _get_secrets()
    if not token or not repo:
        try:
            with open(FILE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    headers = {"Authorization": f"token {token}"}
    r = requests.get(_api_url(repo), headers=headers, timeout=15)
    if r.status_code == 200:
        content = r.json()
        decoded = base64.b64decode(content["content"]).decode("utf-8")
        return json.loads(decoded)
    return {}


def save_data(data):
    token, repo = _get_secrets()
    text = json.dumps(data, ensure_ascii=False, indent=2)

    if not token or not repo:
        with open(FILE_PATH, "w", encoding="utf-8") as f:
            f.write(text)
        return True, "Сохранено локально (data.json)"

    headers = {"Authorization": f"token {token}"}
    url = _api_url(repo)

    r = requests.get(url, headers=headers, timeout=15)
    sha = r.json()["sha"] if r.status_code == 200 else None

    payload = {
        "message": "Update TO data",
        "content": base64.b64encode(text.encode("utf-8")).decode("utf-8"),
    }
    if sha:
        payload["sha"] = sha

    r = requests.put(url, headers=headers, json=payload, timeout=15)
    if r.status_code in (200, 201):
        return True, "Сохранено в GitHub"
    return False, f"Ошибка {r.status_code}: {r.text[:300]}"