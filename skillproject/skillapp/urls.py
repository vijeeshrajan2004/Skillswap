from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),

    path("register/", views.register, name="register"),
    path("login/", views.user_login, name="login"),
    path("logout/", views.user_logout, name="logout"),

    path("about/", views.about, name="about"),
    path("team/", views.team, name="team"),

    path("profile/", views.profile_view, name="profile"),

    path("add-skill/", views.add_skill, name="add_skill"),
    path("matches/", views.matches, name="matches"),
    path("send-request/<int:user_id>/<int:skill_id>/", views.send_request, name="send_request"),

    path("swap-requests/", views.swap_requests, name="swap_requests"),
    path("accept/<int:swap_id>/", views.accept_swap, name="accept_swap"),
    path("reject/<int:swap_id>/", views.reject_swap, name="reject_swap"),
    path("complete/<int:swap_id>/", views.complete_swap, name="complete_swap"),
    path("chat/<int:swap_id>/", views.chat_view, name="chat"),

    path("buy-credits/", views.buy_credits, name="buy_credits"),

    path("withdraw/", views.withdraw_credits, name="withdraw"),
    path("withdraw-history/", views.withdraw_history, name="withdraw_history"),

    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("dashboard/users/", views.admin_users, name="admin_users"),
    path("dashboard/messages/", views.admin_messages, name="admin_messages"),
    path("dashboard/swaps/", views.admin_swaps, name="admin_swaps"),
    path("dashboard/completed-swaps/", views.admin_completed_swaps, name="admin_completed_swaps"),

    path("dashboard/delete-user/<int:user_id>/", views.delete_user, name="delete_user"),
    path("dashboard/delete-message/<int:msg_id>/", views.delete_message, name="delete_message"),
    path("dashboard/delete-swap/<int:swap_id>/", views.delete_swap, name="delete_swap"),

    path("dashboard/withdraws/", views.admin_withdraws, name="admin_withdraws"),
    path("dashboard/withdraw/approve/<int:withdraw_id>/", views.approve_withdraw, name="approve_withdraw"),
    path("dashboard/withdraw/reject/<int:withdraw_id>/", views.reject_withdraw, name="reject_withdraw"),
]