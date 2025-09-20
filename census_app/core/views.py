from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.shortcuts import redirect, render


def home(request):
    return render(request, "core/home.html")


@login_required
def profile(request):
    return render(request, "core/profile.html")


def signup(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("core:home")
    else:
        form = UserCreationForm()
    return render(request, "registration/signup.html", {"form": form})
