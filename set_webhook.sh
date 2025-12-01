import requests

@app.route("/set_webhook")
def set_webhook():
    token = os.environ.get("TG_TOKEN")
    if not token:
        return {"error": "TG_TOKEN not set in environment"}, 500

    # your domain (must be HTTPS)
    domain = request.host_url.rstrip("/")   # example: https://worthwhile-ines-eldro-new-3ee9cf70.koyeb.app

    # your webhook endpoint is /<TOKEN>  (already defined in your app.py)
    webhook_url = f"{domain}/{token}"

    telegram_api = f"https://api.telegram.org/bot{token}/setWebhook"

    res = requests.post(telegram_api, data={"url": webhook_url})

    return res.json(), res.status_code
