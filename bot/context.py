from bot.services.notification_service import NotificationService


class AppContext:
    def __init__(self):
        self.notification_service = NotificationService()

app_context = AppContext()
print(f'{app_context=}')