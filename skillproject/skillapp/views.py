from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.db.models import Q, Sum
import uuid
from .models import *

# HOME / STATIC PAGES
def home(request):
    return render(request, "home.html")


def about(request):
    return render(request, "about.html")


def team(request):
    return render(request, "team.html")

# AUTHENTICATION
def register(request):
    if request.method == "POST":
        name = request.POST["name"]
        email = request.POST["email"]
        phone = request.POST.get("phone", "")
        place = request.POST.get("place", "")
        password = request.POST["password"]
        confirm_password = request.POST["confirm_password"]

        if password != confirm_password:
            messages.error(request, "Passwords do not match!")
            return redirect("register")

        if User.objects.filter(username=email).exists():
            messages.error(request, "Email already registered!")
            return redirect("register")

        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=name,
        )

        Profile.objects.create(
            user=user,
            phone=phone,
            place=place,
            credits=0,
        )

        messages.success(request, "Registration successful! Please login.")
        return redirect("login")

    return render(request, "register.html")


def user_login(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]

        user = authenticate(request, username=username, password=password)

        if user:
            login(request, user)
            return redirect("home")

        messages.error(request, "Invalid email or password")

    return render(request, "login.html")


def user_logout(request):
    logout(request)
    return redirect("home")

# SKILL MANAGEMENT
@login_required
def add_skill(request):
    if request.method == "POST":
        skill_name = request.POST["skill"]
        skill_type = request.POST["type"]

        skill, _ = Skill.objects.get_or_create(name=skill_name)

        UserSkill.objects.create(
            user=request.user,
            skill=skill,
            is_offering=(skill_type == "offer"),
        )

        return redirect("home")

    return render(request, "add_skill.html")


@login_required
def matches(request):
    selected_skill = request.GET.get("skill")

    available_skills = Skill.objects.filter(
        userskill__is_offering=True
    ).distinct()

    my_wanted = UserSkill.objects.filter(
        user=request.user,
        is_offering=False,
    )

    match_list = []

    for item in my_wanted:
        providers = UserSkill.objects.filter(
            skill=item.skill,
            is_offering=True,
        ).exclude(user=request.user)

        providers = providers.exclude(
            skill__swaprequest__requester=request.user,
            skill__swaprequest__status="Completed",
        )

        if selected_skill:
            providers = providers.filter(skill_id=selected_skill)

        match_list.extend(providers)

    match_list = list({m.id: m for m in match_list}.values())

    return render(
        request,
        "matches.html",
        {
            "matches": match_list,
            "available_skills": available_skills,
            "selected_skill": selected_skill,
        },
    )
# SWAP REQUEST SYSTEM
@login_required
def send_request(request, user_id, skill_id):
    if request.method == "POST":
        duration = int(request.POST["duration"])

        if request.user.profile.credits < duration:
            messages.error(request, "Not enough credits!")
            return redirect("matches")

        provider = get_object_or_404(User, id=user_id)
        skill = get_object_or_404(Skill, id=skill_id)

        if SwapRequest.objects.filter(
            requester=request.user,
            provider=provider,
            skill=skill,
            status="Pending",
        ).exists():
            messages.error(request, "Request already sent!")
            return redirect("matches")

        SwapRequest.objects.create(
            requester=request.user,
            provider=provider,
            skill=skill,
            duration=duration,
        )

        messages.success(request, "Swap request sent successfully!")
        return redirect("matches")

    return redirect("matches")


@login_required
def swap_requests(request):
    requests = SwapRequest.objects.filter(
        Q(provider=request.user) | Q(requester=request.user)
    ).order_by("-id")

    return render(request, "swap_requests.html", {"requests": requests})


@login_required
def delete_swap(request, swap_id):
    if not request.user.is_superuser:
        return redirect("home")
    swap = get_object_or_404(SwapRequest, id=swap_id)
    swap.delete()

    messages.success(request, "Swap deleted successfully.")
    return redirect("admin_swaps")


@login_required
def accept_swap(request, swap_id):
    swap = get_object_or_404(SwapRequest, id=swap_id)

    if swap.provider != request.user:
        messages.error(request, "You are not allowed to accept this swap.")
        return redirect("swap_requests")

    if swap.status == "Pending":
        swap.status = "Accepted"
        swap.save()
        messages.success(request, "Swap accepted. Start your session!")

    return redirect("swap_requests")


@login_required
def reject_swap(request, swap_id):
    swap = get_object_or_404(SwapRequest, id=swap_id)

    if swap.provider != request.user:
        messages.error(request, "You are not allowed to reject this swap.")
        return redirect("swap_requests")

    if swap.status == "Pending":
        swap.status = "Rejected"
        swap.save()
        messages.success(request, "Swap rejected.")

    return redirect("swap_requests")


@login_required
def complete_swap(request, swap_id):
    swap = get_object_or_404(SwapRequest, id=swap_id)

    if swap.provider != request.user:
        messages.error(request, "You are not allowed to complete this swap.")
        return redirect("swap_requests")

    if swap.status == "Accepted":
        minutes = swap.duration

        if swap.requester.profile.credits >= minutes:
            swap.requester.profile.credits -= minutes
            swap.requester.profile.save()

            swap.provider.profile.credits += minutes
            swap.provider.profile.save()

            UserSkill.objects.filter(
                user=swap.requester,
                skill=swap.skill,
                is_offering=False,
            ).delete()

            swap.status = "Completed"
            swap.save()

            messages.success(request, "Session completed. Coins transferred!")
        else:
            messages.error(request, "Student does not have enough coins!")

    return redirect("swap_requests")

# PAYMENTS
@login_required
def buy_credits(request):
    if request.method == "POST":
        amount = int(request.POST.get("amount"))
        upi_id = request.POST.get("upi_id")

        if amount <= 0:
            messages.error(request, "Invalid amount.")
            return redirect("buy_credits")

        if "@" not in upi_id:
            messages.error(request, "Invalid UPI ID.")
            return redirect("buy_credits")

        txn_id = str(uuid.uuid4())[:12].upper()

        request.user.profile.credits += amount
        request.user.profile.save()

        Payment.objects.create(
            user=request.user,
            amount=amount,
            transaction_id=txn_id,
        )

        messages.success(request, f"Payment Successful! ₹{amount} added. TXN: {txn_id}")
        return redirect("buy_credits")

    return render(request, "buy_credits.html")
# CHAT SYSTEM
@login_required
def chat_view(request, swap_id):
    swap = get_object_or_404(SwapRequest, id=swap_id)

    if request.user not in [swap.requester, swap.provider]:
        return redirect("home")

    if request.method == "POST":
        text = request.POST.get("text")
        if text:
            Message.objects.create(
                swap=swap,
                sender=request.user,
                text=text,
            )
        return redirect("chat", swap_id=swap.id)

    messages_list = swap.messages.order_by("timestamp")

    return render(
        request,
        "chat.html",
        {
            "swap": swap,
            "messages": messages_list,
        },
    )
# PROFILE
@login_required
def profile_view(request):
    if request.method == "POST":

        if "update_profile" in request.POST:
            request.user.first_name = request.POST.get("name")
            request.user.email = request.POST.get("email")
            request.user.save()

            request.user.profile.phone = request.POST.get("phone")
            request.user.profile.place = request.POST.get("place")
            request.user.profile.save()

            messages.success(request, "Profile updated successfully!")
            return redirect("profile")

        if "change_password" in request.POST:
            form = PasswordChangeForm(request.user, request.POST)

            if form.is_valid():
                user = form.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Password changed successfully!")
                return redirect("profile")

            messages.error(request, "Password change failed.")

    form = PasswordChangeForm(request.user)
    return render(request, "profile.html", {"form": form})

# WITHDRAW SYSTEM
@login_required
def withdraw_credits(request):
    if request.method == "POST":
        amount = int(request.POST.get("amount"))
        upi_id = request.POST.get("upi_id")

        if amount <= 0:
            messages.error(request, "Invalid amount.")
            return redirect("withdraw")

        if amount > request.user.profile.credits:
            messages.error(request, "Not enough credits!")
            return redirect("withdraw")

        WithdrawRequest.objects.create(
            user=request.user,
            amount=amount,
            upi_id=upi_id,
            status="Pending",
        )

        messages.success(request, "Withdraw request submitted successfully!")
        return redirect("withdraw")

    return render(request, "withdraw.html")


@login_required
def withdraw_history(request):
    history = WithdrawRequest.objects.filter(
        user=request.user
    ).order_by("-created_at")

    return render(request, "withdraw_history.html", {"history": history})

# ADMIN PANEL
@login_required
def admin_dashboard(request):
    if not request.user.is_superuser:
        return redirect("home")

    total_users = User.objects.count()
    total_skills = Skill.objects.count()
    total_swaps = SwapRequest.objects.count()
    completed_swaps = SwapRequest.objects.filter(status="Completed").count()
    pending_swaps = SwapRequest.objects.filter(status="Pending").count()
    total_messages = Message.objects.count()

    total_coins = SwapRequest.objects.filter(
        status="Completed"
    ).aggregate(Sum("duration"))["duration__sum"] or 0

    total_withdraws = WithdrawRequest.objects.count()
    pending_withdraws = WithdrawRequest.objects.filter(status="Pending").count()
    approved_withdraws = WithdrawRequest.objects.filter(status="Approved").count()

    total_withdraw_amount = WithdrawRequest.objects.filter(
        status="Approved"
    ).aggregate(Sum("amount"))["amount__sum"] or 0

    recent_swaps = SwapRequest.objects.order_by("-id")[:5]
    recent_users = User.objects.order_by("-id")[:5]

    context = {
        "total_users": total_users,
        "total_skills": total_skills,
        "total_swaps": total_swaps,
        "completed_swaps": completed_swaps,
        "pending_swaps": pending_swaps,
        "total_messages": total_messages,
        "total_coins": total_coins,
        "total_withdraws": total_withdraws,
        "pending_withdraws": pending_withdraws,
        "approved_withdraws": approved_withdraws,
        "total_withdraw_amount": total_withdraw_amount,
        "recent_swaps": recent_swaps,
        "recent_users": recent_users,
    }

    return render(request, "admin_dashboard.html", context)


@login_required
def admin_users(request):
    if not request.user.is_superuser:
        return redirect("home")

    users = User.objects.all()
    return render(request, "admin_users.html", {"users": users})


@login_required
def admin_messages(request):
    if not request.user.is_superuser:
        return redirect("home")

    messages_list = Message.objects.all().order_by("-timestamp")
    return render(request, "admin_messages.html", {"messages": messages_list})


@login_required
def admin_swaps(request):
    if not request.user.is_superuser:
        return redirect("home")

    if request.method == "POST":
        swap_id = request.POST.get("swap_id")
        new_status = request.POST.get("status")

        swap = get_object_or_404(SwapRequest, id=swap_id)
        swap.status = new_status
        swap.save()

        messages.success(request, f"Swap status updated to {new_status}")
        return redirect("admin_swaps")

    swaps = SwapRequest.objects.all().order_by("-id")
    return render(request, "admin_swaps.html", {"swaps": swaps})


@login_required
def admin_completed_swaps(request):
    if not request.user.is_superuser:
        return redirect("home")

    completed = SwapRequest.objects.filter(
        status="Completed"
    ).order_by("-id")

    return render(request, "admin_completed_swaps.html", {"swaps": completed})


@login_required
def admin_withdraws(request):
    if not request.user.is_superuser:
        return redirect("home")

    withdraws = WithdrawRequest.objects.all().order_by("-created_at")
    return render(request, "admin_withdraws.html", {"withdraws": withdraws})

@login_required
def delete_user(request, user_id):
    if not request.user.is_superuser:
        return redirect("home")

    user = get_object_or_404(User, id=user_id)

    if user == request.user:
        messages.error(request, "You cannot delete yourself.")
        return redirect("admin_users")

    user.delete()
    messages.success(request, "User deleted successfully.")
    return redirect("admin_users")
@login_required
def delete_message(request, msg_id):
    if not request.user.is_superuser:
        return redirect("home")

    msg = get_object_or_404(Message, id=msg_id)
    msg.delete()

    messages.success(request, "Message deleted successfully.")
    return redirect("admin_messages")

@login_required
def approve_withdraw(request, withdraw_id):
    if not request.user.is_superuser:
        return redirect("home")

    withdraw = get_object_or_404(WithdrawRequest, id=withdraw_id)

    if withdraw.status == "Pending":
        profile = withdraw.user.profile

        if profile.credits >= withdraw.amount:
            profile.credits -= withdraw.amount
            profile.save()

            withdraw.status = "Approved"
            withdraw.save()

            messages.success(request, "Withdraw approved successfully.")
        else:
            messages.error(request, "User does not have enough credits.")

    return redirect("admin_withdraws")


@login_required
def reject_withdraw(request, withdraw_id):
    if not request.user.is_superuser:
        return redirect("home")

    withdraw = get_object_or_404(WithdrawRequest, id=withdraw_id)

    if withdraw.status == "Pending":
        withdraw.status = "Rejected"
        withdraw.save()
        messages.success(request, "Withdraw rejected.")

    return redirect("admin_withdraws")