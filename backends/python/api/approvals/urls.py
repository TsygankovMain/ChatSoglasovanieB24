from django.urls import path
from .views import approval_create, approval_list, approval_detail, approval_cancel, vote_handle

urlpatterns = [
    path("api/approval/create", approval_create, name="approval_create"),
    path("api/approval/list", approval_list, name="approval_list"),
    path("api/approval/cancel", approval_cancel, name="approval_cancel"),
    path("api/approval/<str:request_id>", approval_detail, name="approval_detail"),
    path("api/vote/handle", vote_handle, name="vote_handle"),
]
