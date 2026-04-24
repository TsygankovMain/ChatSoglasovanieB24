from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.clickjacking import xframe_options_exempt

from .utils.decorators import auth_required, log_errors
from .utils import AuthorizedRequest
from .models import ApplicationInstallation

from config import load_config, config
from approvals.b24_client import ApprovalB24Client

__all__ = [
    "root",
    "health",
    "get_enum",
    "get_list",
    "install",
    "get_token",
]

config = load_config()


@xframe_options_exempt
@require_GET
@log_errors("root")
@auth_required
def root(request: AuthorizedRequest):
    return JsonResponse({"message": "Python Backend is running"})


@xframe_options_exempt
@require_GET
@log_errors("health")
@auth_required
def health(request: AuthorizedRequest):
    return JsonResponse({
        "status": "healthy",
        "backend": "python",
        "timestamp": timezone.now().timestamp(),
    })


@xframe_options_exempt
@require_GET
@log_errors("get_enum")
@auth_required
def get_enum(request: AuthorizedRequest):
    options = ["option 1", "option 2", "option 3"]
    return JsonResponse(options, safe=False)


@xframe_options_exempt
@require_GET
@log_errors("get_list")
@auth_required
def get_list(request: AuthorizedRequest):
    elements = ["element 1", "element 2", "element 3"]
    return JsonResponse(elements, safe=False)


@xframe_options_exempt
@csrf_exempt
@require_POST
@log_errors("install")
@auth_required
def install(request: AuthorizedRequest):
    bitrix24_account = request.bitrix24_account

    ApplicationInstallation.objects.update_or_create(
        bitrix_24_account=bitrix24_account,
        defaults={
            "status": bitrix24_account.status,
            "portal_license_family": "",
            "application_token": bitrix24_account.application_token,
        },
    )

    import logging
    logger = logging.getLogger(__name__)

    b24 = ApprovalB24Client(bitrix24_account)
    steps = {}

    try:
        b24.create_entity_storages()
        steps["entity_storages"] = "ok"
    except Exception as e:
        steps["entity_storages"] = str(e)

    webhook_url = f"{config.app_base_url}/api/vote/handle"
    try:
        bot_id = b24.register_bot("Согласование", webhook_url)
        if bot_id:
            b24.set_app_option("BOT_ID", bot_id)
        steps["bot"] = f"ok, id={bot_id}"
    except Exception as e:
        steps["bot"] = str(e)

    try:
        b24.bind_placement("IM_TEXTAREA", f"{config.app_base_url}/")
        steps["placement"] = "ok"
    except Exception as e:
        steps["placement"] = str(e)

    logger.info("Install steps: %s", steps)
    return JsonResponse({"message": "Installation successful", "steps": steps})


@xframe_options_exempt
@csrf_exempt
@require_POST
@log_errors("get_token")
@auth_required
def get_token(request: AuthorizedRequest):
    return JsonResponse({"token": request.bitrix24_account.create_jwt_token()})
