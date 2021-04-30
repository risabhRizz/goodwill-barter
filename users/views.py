from django.shortcuts import render, redirect, reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from .forms import *
from users.models import Message, Barter
from products.models import Product
from django.db.models import Q, F


def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Your account has been created! You are now able to login: {username}')
            return redirect('login')
    else:
        form = UserRegisterForm()

    return render(request, 'users/register.html', {'form': form})


@login_required
def profile(request):
    if request.method == 'POST':
        # instance param will populate the form
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)

        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()

            messages.success(request, f'Your account has been updated!')
            return redirect('profile')
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm(instance=request.user.profile)

    context = {
        'u_form': u_form,
        'p_form': p_form
    }
    return render(request, 'users/profile.html', context)


@login_required
def chat_history(request):
    chat_users = set()

    for usr in Message.objects.filter(receiver=request.user).values('sender').distinct():
        user_id = usr['sender']
        user_obj = User.objects.get(pk=user_id)
        chat_users.add(user_obj)

    for usr in Message.objects.filter(sender=request.user).values('receiver').distinct():
        user_id = usr['receiver']
        user_obj = User.objects.get(pk=user_id)
        chat_users.add(user_obj)

    context = {'chat_users': chat_users}
    return render(request, 'users/chat_history.html', context)


@login_required
def chat(request):
    context = {}
    receiver_name = request.GET.get('receiver')
    other_user = User.objects.get(username=receiver_name)
    current_user = request.user

    msg_data = {'msg_history': Message.objects.filter(
        (Q(sender=current_user) & Q(receiver=other_user)) |
        (Q(sender=other_user) & Q(receiver=current_user))).order_by('created_at')}
    context['msg_data'] = msg_data

    if request.method == 'POST':
        msg_instance = Message(sender=request.user, receiver=User.objects.get(username=receiver_name))
        form = SendMsgForm(request.POST, instance=msg_instance)
        if form.is_valid():
            form.save()
            messages.success(request, f'Message sent to: {receiver_name}')

        return redirect(reverse('chat-page') + f'?receiver={receiver_name}')
    else:
        form = SendMsgForm()

    context['form'] = form

    return render(request, 'users/chat.html', context)


@login_required
def barter_req_history(request):
    context = {}
    receiver_name = request.GET.get('receiver')
    print(f"Receiver: {receiver_name}")

    barter_users = set()
    for barter in Barter.objects.filter(
            (Q(user1=request.user) & Q(status=True)) | (Q(user2=request.user) & Q(status=True))):
        if barter.product2 is None:
            for other_barter in Barter.objects.filter(Q(user1=barter.user2) & Q(user2=barter.user1) & Q(status=True)):
                if other_barter.product2 is None:
                    if other_barter.user1 == request.user:
                        barter_obj = Barter(user1=request.user, product1=other_barter.product1,
                                            user2=other_barter.user2, product2=barter.product1, status=True)
                    else:
                        barter_obj = Barter(user1=request.user, product1=barter.product1, user2=barter.user2,
                                            product2=other_barter.product1, status=True)
                    print(f"barter_obj: {barter_obj}")
                    barter_obj.save()
                    b = Barter.objects.filter(Q(status=True))
                    print(f"bbbbbbbbb: {b}")
                    barter_users.add(barter_obj.user2)
                    Barter.objects.filter(id=barter.pk).delete()
                    Barter.objects.filter(id=other_barter.pk).delete()
                    remove_product(barter_obj)
        else:
            print(f"barter_obj: {barter}")
            barter_users.add(barter.user1)
            barter_users.add(barter.user2)

    pending_users = set()
    for pending in Barter.objects.filter(Q(user1=request.user) | Q(user2=request.user)):
        if pending.product2 is None:
            pending_users.add(pending.user1)
            pending_users.add(pending.user2)

    context['barter_users'] = barter_users
    context['pending_users'] = pending_users

    return render(request, 'users/barter_history.html', context)


def remove_product(barter):
    prod1 = Product.objects.get(id=barter.product1.pk)
    if prod1.category != 'service':
        prod1.available = False
        prod1.save()

    prod2 = Product.objects.get(id=barter.product2.pk)
    if prod2.category != 'service':
        prod2.available = False
        prod2.save()

    for remove_barter in Barter.objects.filter(Q(product1=barter.product1)):
        if remove_barter.product1.category != 'service' and remove_barter.product2 is None:
            Barter.objects.filter(id=remove_barter.pk).delete()
    for remove_barter in Barter.objects.filter(Q(product1=barter.product2)):
        if remove_barter.product1.category != 'service' and remove_barter.product2 is None:
            Barter.objects.filter(id=remove_barter.pk).delete()


def create_barter_entry(prod_owner, sender, prod, context):
    for pending_barter in Barter.objects.filter((Q(user1=prod_owner) & Q(user2=sender))):
        if pending_barter.product2 is None:
            context['pending_barter1'] = pending_barter
            context['status1'] = pending_barter.status
            return False

    if prod:
        barter_obj = Barter(user1=prod_owner, product1=prod, user2=sender)
        barter_obj.save()
        print("Barter object created")
        context['pending_barter1'] = barter_obj
        return True


@login_required
def barter_req(request):
    context = {}
    prod = None
    receiver_name = request.GET.get('receiver')
    print(f"Receiver: {receiver_name}")
    recv_user = User.objects.get(username=receiver_name)
    context['prod_owner'] = recv_user

    if 'product_key' in request.GET:
        recv_user_prod_key = request.GET.get('product_key')
        print(f"Product of user2: {recv_user_prod_key}")
        prod = Product.objects.get(pk=recv_user_prod_key)
        context['prod_interested'] = prod

    if 'accept' in request.GET:
        barter_requests = Barter.objects.filter(
            (Q(user1=request.user) & Q(user2=recv_user) & Q(status=False)))
        if barter_requests:
            barter_requests[0].status = True
            barter_requests[0].save()

    if 'decline' in request.GET:
        barter_requests = Barter.objects.filter(
            (Q(user1=request.user) & Q(user2=recv_user) & Q(status=False)))
        if barter_requests:
            Barter.objects.filter(id=barter_requests[0].pk).delete()

    if 'status' in request.GET:
        completed_barters = set()
        for barter_complete in Barter.objects.filter((Q(user1=request.user) & Q(user2=recv_user) & Q(status=True)) | (
                Q(user1=recv_user) & Q(user2=request.user) & Q(status=True))):
            if barter_complete.product2 != None:
                completed_barters.add(barter_complete)
        context['completed_barters'] = completed_barters
    else:
        is_created = create_barter_entry(recv_user, request.user, prod, context)
        context['is_created'] = is_created
        if not is_created:
            print("Could not create barter req")

        for pending_barter in Barter.objects.filter((Q(user1=request.user) & Q(user2=recv_user))):
            if pending_barter.product2 is None:
                context['pending_barter2'] = pending_barter
                context['status2'] = pending_barter.status

    return render(request, 'users/barter.html', context)
