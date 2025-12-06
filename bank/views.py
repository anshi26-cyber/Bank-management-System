# app/views.py  (updated)

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from .models import Account, Transaction
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from django.db import DatabaseError
from datetime import datetime
from django.http import HttpResponse
from decimal import Decimal, InvalidOperation

import csv

def home(request):
    return render(request, "home.html")


def login_user(request):
    message = None
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()

        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect("home")
        else:
            message = "Invalid username or password."

    return render(request, "login.html", {"message": message})


def register_user(request):
    message = None
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "").strip()
        confirm = request.POST.get("confirm", "").strip()

        if password != confirm:
            message = "Passwords do not match."
            return render(request, "register.html", {"message": message})

        if User.objects.filter(username=username).exists():
            message = "Username already taken."
            return render(request, "register.html", {"message": message})

        user = User.objects.create_user(username=username, email=email, password=password)
        login(request, user)
        return redirect("home")

    return render(request, "register.html", {"message": message})


def logout_user(request):
    logout(request)
    return redirect("login")


@login_required(login_url='login')
def profile(request):
    user = request.user

    # handle profile edit POST
    if request.method == "POST":
        first_name = (request.POST.get("first_name") or "").strip()
        last_name = (request.POST.get("last_name") or "").strip()
        email = (request.POST.get("email") or "").strip()

        # simple validation
        if not email:
            messages.error(request, "Email is required.")
            return redirect("profile")

        # check if another user already has this email
        other = User.objects.filter(email=email).exclude(pk=user.pk).first()
        if other:
            messages.error(request, "This email is already used by another account.")
            return redirect("profile")

        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.save()

        messages.success(request, "Profile updated successfully.")
        return redirect("profile")

    # GET: prepare context
    accounts = Account.objects.filter(user=user)

    # safer fetch for recent transactions: avoid hard crash if DB schema isn't synced
    try:
        recent_transactions = Transaction.objects.filter(account__user=user).order_by('-timestamp')[:6]
    except DatabaseError:
        # fallback so profile still loads while you fix migrations/schema
        recent_transactions = []

    context = {
        "user": user,
        "accounts": accounts,
        "recent_transactions": recent_transactions,
    }
    return render(request, "profile.html", context)

@login_required(login_url='login')
def create_account(request):
    message = None
    if request.method == "POST":
        acc_no = (request.POST.get("account_number") or "").strip()
        balance_raw = (request.POST.get("balance") or "0").strip()

        if not acc_no:
            message = "Account number required."
            return render(request, "create_account.html", {"message": message})

        # avoid duplicate account numbers
        if Account.objects.filter(account_number=acc_no).exists():
            message = "Account number already exists."
            return render(request, "create_account.html", {"message": message})

        # parse balance safely using Decimal
        try:
            balance = Decimal(balance_raw)
            if balance < Decimal("0"):
                raise InvalidOperation
        except (InvalidOperation, ValueError, TypeError):
            message = "Invalid balance amount."
            return render(request, "create_account.html", {"message": message})

        # create account for the logged-in user
        Account.objects.create(user=request.user, account_number=acc_no, balance=balance)

        # redirect to profile so the user sees the new account immediately
        return redirect("profile")

    return render(request, "create_account.html")

def deposit(request):
    message = None
    if request.method == "POST":
        acc_no = (request.POST.get("account") or "").strip()
        amount_raw = (request.POST.get("amount") or "").strip()

        if not acc_no:
            message = "Account number required."
            return render(request, "deposit.html", {"message": message})

        try:
            amount = Decimal(amount_raw)
            if amount <= Decimal("0"):
                raise InvalidOperation
        except (InvalidOperation, ValueError, TypeError):
            message = "Enter a valid positive amount."
            return render(request, "deposit.html", {"message": message})

        try:
            account = Account.objects.get(account_number=acc_no)
        except Account.DoesNotExist:
            message = f"No account found with number {acc_no}."
            return render(request, "deposit.html", {"message": message})

        # safe decimal math
        account.balance = account.balance + amount
        account.save()
        Transaction.objects.create(account=account, txn_type="DP", amount=amount, description="Deposit")
        message = f"Deposit successful. New balance: {account.balance:.2f}"
        return render(request, "deposit.html", {"message": message})

    return render(request, "deposit.html")


def withdraw(request):
    message = None
    if request.method == "POST":
        acc_no = (request.POST.get("account") or "").strip()
        amount_raw = (request.POST.get("amount") or "").strip()

        if not acc_no:
            message = "Account number required."
            return render(request, "withdraw.html", {"message": message})

        try:
            amount = Decimal(amount_raw)
            if amount <= Decimal("0"):
                raise InvalidOperation
        except (InvalidOperation, ValueError, TypeError):
            message = "Enter a valid positive amount."
            return render(request, "withdraw.html", {"message": message})

        try:
            account = Account.objects.get(account_number=acc_no)
        except Account.DoesNotExist:
            message = f"No account found with number {acc_no}."
            return render(request, "withdraw.html", {"message": message})

        if account.balance < amount:
            message = "Insufficient balance."
            return render(request, "withdraw.html", {"message": message})

        account.balance = account.balance - amount
        account.save()
        Transaction.objects.create(account=account, txn_type="WD", amount=amount, description="Withdraw")
        message = f"Withdraw successful. New balance: {account.balance:.2f}"
        return render(request, "withdraw.html", {"message": message})

    return render(request, "withdraw.html")


def transfer(request):
    message = None
    if request.method == "POST":
        from_no = (request.POST.get("from") or "").strip()
        to_no = (request.POST.get("to") or "").strip()
        amount_raw = (request.POST.get("amount") or "").strip()

        if not from_no or not to_no:
            message = "Both From and To account numbers are required."
            return render(request, "transfer.html", {"message": message})

        try:
            amount = Decimal(amount_raw)
            if amount <= Decimal("0"):
                raise InvalidOperation
        except (InvalidOperation, ValueError, TypeError):
            message = "Enter a valid positive amount."
            return render(request, "transfer.html", {"message": message})

        try:
            from_acc = Account.objects.get(account_number=from_no)
        except Account.DoesNotExist:
            message = f"No sender account found with number {from_no}."
            return render(request, "transfer.html", {"message": message})

        try:
            to_acc = Account.objects.get(account_number=to_no)
        except Account.DoesNotExist:
            message = f"No receiver account found with number {to_no}."
            return render(request, "transfer.html", {"message": message})

        if from_acc.balance < amount:
            message = "Insufficient balance in sender account."
            return render(request, "transfer.html", {"message": message})

        from_acc.balance = from_acc.balance - amount
        to_acc.balance = to_acc.balance + amount
        from_acc.save()
        to_acc.save()

        Transaction.objects.create(account=from_acc, txn_type="TR", amount=amount, description=f"Transfer to {to_no}")
        Transaction.objects.create(account=to_acc, txn_type="RC", amount=amount, description=f"Received from {from_no}")

        message = f"Transfer successful. Sender new balance: {from_acc.balance:.2f}"
        return render(request, "transfer.html", {"message": message})

    return render(request, "transfer.html")

# --------------------------
# NEW: Transactions history view
# --------------------------
@login_required(login_url='login')
def transactions_list(request):
    """
    Transactions page:
    - GET params: q (search in account number or description), txn_type, from_date (YYYY-MM-DD), to_date (YYYY-MM-DD)
    - pagination: page (default 1), 10 per page
    - export csv: add ?export=csv to download
    """
    qs = Transaction.objects.select_related('account', 'account__user').all()

    # read filters
    q = request.GET.get('q', '').strip()
    txn_type = request.GET.get('txn_type', '').strip()
    from_date = request.GET.get('from_date', '').strip()
    to_date = request.GET.get('to_date', '').strip()
    export = request.GET.get('export', '').strip().lower()

    # search by account number or description
    if q:
        qs = qs.filter(
            Q(account__account_number__icontains=q) |
            Q(description__icontains=q)
        )

    # txn_type should match short code exactly (e.g. 'DP','WD','TR','RC','CR','DR')
    if txn_type:
        qs = qs.filter(txn_type=txn_type)

    # date filters
    if from_date:
        try:
            dt = datetime.strptime(from_date, "%Y-%m-%d")
            qs = qs.filter(timestamp__date__gte=dt.date())
        except ValueError:
            pass
    if to_date:
        try:
            dt = datetime.strptime(to_date, "%Y-%m-%d")
            qs = qs.filter(timestamp__date__lte=dt.date())
        except ValueError:
            pass

    qs = qs.order_by('-timestamp')

    # CSV export (readable type)
    if export == 'csv':
        filename = f"transactions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        writer = csv.writer(response)
        writer.writerow(['Timestamp', 'Account', 'Owner', 'Type', 'Amount', 'Description'])
        for t in qs:
            writer.writerow([
                t.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                t.account.account_number,
                t.account.user.username,
                t.get_txn_type_display(),
                f"{t.amount:.2f}",
                t.description or ""
            ])
        return response

    # pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(qs, 10)
    try:
        transactions = paginator.page(page)
    except PageNotAnInteger:
        transactions = paginator.page(1)
    except EmptyPage:
        transactions = paginator.page(paginator.num_pages)

    context = {
        'transactions': transactions,
        'q': q,
        'txn_type': txn_type,
        'from_date': from_date,
        'to_date': to_date,
    }
    return render(request, 'transactions.html', context)
