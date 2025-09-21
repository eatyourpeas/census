from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.shortcuts import redirect, render
from django.contrib import messages
from django.db import transaction
from census_app.surveys.models import Organization, OrganizationMembership
from .forms import SignupForm


def home(request):
    return render(request, "core/home.html")


@login_required
def profile(request):
    if request.method == "POST" and request.POST.get("action") == "upgrade_to_org":
        # Create a new organisation owned by this user, and make them ADMIN
        with transaction.atomic():
            org_name = request.POST.get("org_name") or f"{request.user.username}'s Organisation"
            org = Organization.objects.create(name=org_name, owner=request.user)
            OrganizationMembership.objects.get_or_create(organization=org, user=request.user, defaults={"role": OrganizationMembership.Role.ADMIN})
        messages.success(request, "Organisation created. You are now an organisation admin and can host surveys and build a team.")
        return redirect("surveys:org_users", org_id=org.id)
    return render(request, "core/profile.html")


def signup(request):
    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            account_type = request.POST.get("account_type")
            if account_type == "org":
                with transaction.atomic():
                    org_name = request.POST.get("org_name") or f"{user.username}'s Organisation"
                    org = Organization.objects.create(name=org_name, owner=user)
                    OrganizationMembership.objects.create(organization=org, user=user, role=OrganizationMembership.Role.ADMIN)
                messages.success(request, "Organisation created. You are an organisation admin.")
                return redirect("surveys:org_users", org_id=org.id)
            return redirect("core:home")
    else:
        form = SignupForm()
    return render(request, "registration/signup.html", {"form": form})
