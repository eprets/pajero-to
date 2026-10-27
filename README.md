# Лист ТО — Mitsubishi Pajero IV 3.0 (2013)

Веб-трекер регламентного обслуживания. Регламент: ТО-1 = 1 000 км, шаг 10 000 км, всего ТО-56 (до 550 000 км).

## Запуск локально
pip install -r requirements.txt
streamlit run app.py

## Деплой на Streamlit Cloud
1. Репозиторий должен быть на GitHub (публичный).
2. На share.streamlit.io → New app → выбрать репо, ветку, app.py.
3. В Advanced settings → Secrets добавить:
   GITHUB_TOKEN = "ghp_..."
   GITHUB_REPO = "ваш_логин/pajero-to"

  