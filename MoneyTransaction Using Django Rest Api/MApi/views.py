from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.decorators import api_view
from rest_framework.views import APIView
from rest_framework.response import Response
from .serializer import UserRegistrationSerializer ,WalletSerializer,TransactionSerializer,UserLoginSerializer
from django.shortcuts import get_object_or_404
from .models import User,Wallet,Transactions
from rest_framework.permissions import IsAuthenticated

from rest_framework import status
from django.utils import timezone
from django.contrib.auth import authenticate


def get_tokens_for_user(user):
  refresh = RefreshToken.for_user(user)
  return {
      'refresh': str(refresh),
      'access': str(refresh.access_token),
  }


## user register ##
@api_view(['POST'])
def register_user(request):
    phone=request.data.get('phone_number')
    if User.objects.filter(phone_number=phone).exists():
        return Response('phone number is exists')
    else:
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({"message": "User registered successfully!"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class UserLoginView(APIView):
  permission_classes = []
  def post(self, request, format=None):
    serializer = UserLoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    phone_number = serializer.data.get('phone_number')
    password = serializer.data.get('password')
    user = authenticate(phone_number=phone_number, password=password)
    if user is not None:
      token = get_tokens_for_user(user)
      return Response({'token':token, 'msg':'Login Success'}, status=status.HTTP_200_OK)
    else:
      return Response({'errors':{'non_field_errors':['phone_number or Password is not Valid']}}, status=status.HTTP_404_NOT_FOUND)
     
     
         
        
## create a  wallet ##
@api_view(['POST'])
def create_wallet(request, id):
    permission_classes = [IsAuthenticated]
    phone = request.data.get('phone_number')
    user = get_object_or_404(User, pk=id)

    if user.phone_number == phone and not Wallet.objects.filter(phone_number=phone):
        serializer = WalletSerializer(data=request.data, partial=True)
        serializer.user = user
        if serializer.is_valid():
            serializer.save(user=user)
            return Response({"message": "Wallet created successfully!"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    else:
        return Response({"message": "wallet with this number is already exists"}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def send_money(request,id):
    permission_classes = [IsAuthenticated]
    phone = request.data.get('reciver_phone_number')
    amount = float(request.data.get('amount'))
    sender_phone=get_object_or_404(User,pk=id).phone_number

    try:
        rec_wallet = Wallet.objects.get(phone_number=phone)
        send_wallet = Wallet.objects.get(phone_number=sender_phone)
    except Wallet.DoesNotExist:
        return Response({"message": "No account found with the provided phone number"}, status=status.HTTP_400_BAD_REQUEST)
    except Wallet.MultipleObjectsReturned:
        return Response({"message": "Multiple accounts found with the provided phone number"}, status=status.HTTP_400_BAD_REQUEST)
    if phone != sender_phone:
        if send_wallet.balance >= amount:
            rec_wallet.balance += amount
            rec_wallet.save()
            send_wallet.balance -= amount
            send_wallet.save()

            transaction = Transactions.objects.create(
                wallet=send_wallet,
                sender_phone=send_wallet.phone_number,
                receiver_phone=rec_wallet.phone_number,
                amount=amount,
                date_time=timezone.now()
            )
            serializer=TransactionSerializer(transaction)
            return Response({"data":serializer.data,"message": "amount transfer succesfully"}, status=status.HTTP_201_CREATED)
        return Response({"message": "insufficient balance"}, status=status.HTTP_400_BAD_REQUEST)
    return Response({"message": "not allow same phone number"}, status=status.HTTP_400_BAD_REQUEST)
    

## for bank ##
@api_view(['POST'])
def add_money(request,wallet_id):
        permission_classes = [IsAuthenticated]
        amount=int(request.data.get('amount'))
        wallet=get_object_or_404(Wallet,pk=wallet_id)
        wallet+=amount
        wallet.save()
        return Response({"amount added succussfully"})


@api_view(['GET'])
def transactions(request,id):
        permission_classes = [IsAuthenticated]
        user=get_object_or_404(User,pk=id)
        wallet=get_object_or_404(Wallet,user=user)
        data=Transactions.objects.filter(wallet=wallet)
        serializer=TransactionSerializer(data,many=True)
        return Response(serializer.data)