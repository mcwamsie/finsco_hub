from fisco_hub_8d import settings


def application_settings(request):
    """
    Return a lazy 'messages' context variable as well as
    'DEFAULT_MESSAGE_LEVELS'.
    """
    return {
        "app_name": settings.APP_NAME,
    }
