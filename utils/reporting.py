import csv
import os
from datetime import datetime


def export_user_actions_to_csv(actions, filename=None):
    """
    actions — список словарей:
    [
      {
        'user_id': ...,
        'telegram_id': ...,
        'username': ...,
        'action': ...,
        'details': ...,
        'created_at': datetime(...)
      },
      ...
    ]
    """
    if filename is None:
        os.makedirs("reports", exist_ok=True)
        filename = f"reports/user_actions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    os.makedirs(os.path.dirname(filename), exist_ok=True)

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow(["user_id", "telegram_id", "username", "action", "details", "created_at"])
        for a in actions:
            writer.writerow([
                a.get("user_id"),
                a.get("telegram_id"),
                a.get("username") or "",
                a.get("action") or "",
                a.get("details") or "",
                a.get("created_at").strftime("%Y-%m-%d %H:%M:%S")
                if a.get("created_at") else ""
            ])

    return filename

