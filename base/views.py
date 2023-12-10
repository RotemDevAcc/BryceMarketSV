from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.views import APIView
from rest_framework.response import Response
# from django.contrib.auth.models import User
# from .models import UserProfile, Product, Category, Receipt
from .models import MarketUser, Product, Category, Receipt
from .serializer import UserSerializer, ProductSerializer, CategorySerializer, ReceiptSerializer
# from .serializer import UserSerializer, ProductSerializer, CategorySerializer, ReceiptSerializer
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.contrib.auth.password_validation import validate_password
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.storage import default_storage
import json, os
from decimal import Decimal


class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
 
        # Add custom claims
        token['username'] = user.username
        token['firstname'] = user.firstname
        token['lastname'] = user.lastname
        token['email'] = user.email
        token['gender'] = user.gender
        token['dob'] = user.date_of_birth.isoformat() if user.date_of_birth else None
        token['img'] = str(user.img) or "placeholder.png"
        token['is_staff'] = user.is_staff or None
        return token
 
 
class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer

#def is_user_admin(user):
    #if not user or user == None:
        #return
    
    #print(is_user_admin(request.user))

    #return user.is_staff

@api_view(['GET'])
def index(request):
    return JsonResponse('hello', safe=False)



@api_view(["GET","POST"])
def productlist(request):
    if not request.method: return
    if request.method == "GET":
        products = Product.objects.all()
        serializer = ProductSerializer(products, many=True)
        
        categories = Category.objects.all()
        serializer2 = CategorySerializer(categories, many=True)

        # Combine the serialized data into a single dictionary
        combined_data = {
            'products': serializer.data,
            'categories': serializer2.data,
        }
        return Response(combined_data)
    elif request.method == "POST":
        user = request.user
        price = Decimal(str(request.data['price']))
        cart = request.data['cart']
        totalPrice = Decimal('0')

        PurchasedItems = []
        try:
            for item_info in cart:
                item_id = item_info.get('id')
                product = Product.objects.get(id=item_id)
                if product:
                    if product.price == Decimal(item_info['price']):
                        itemprice = Decimal(item_info['price'])
                        totalPrice += (itemprice * item_info['count'])
                        PurchasedItems.append({
                            "item": item_id,
                            "count": item_info['count'],
                            "price": float((itemprice * item_info['count']).quantize(Decimal('0.01')))
                        })
                    else:
                        print("Warning, Wrong Price")
                        return Response({"state": "fail", "msg": "ERROR, Something went wrong."})
                else:
                    print("Warning, Unauthorized Item Detected.")
                    return Response({"state": "fail", "msg": "ERROR, Something went wrong."})
            if totalPrice == price:
                user_instance = MarketUser.objects.get(username=user)

                receipt_data = {
                    'products': json.dumps(PurchasedItems),
                    'price': float(totalPrice),
                    'user': user_instance.id
                }

                serializer = ReceiptSerializer(data=receipt_data)
                if serializer.is_valid():
                    serializer.save()
                    print("Receipt saved successfully")
                    return Response({"state": "success", "msg": f"Purchase Complete, You Bought All The Specificed Items For ${totalPrice}"})
                else:
                    print("Error in data:", serializer.errors)
            else:
                print(f"Warning Wrong Price Client Reported: {type(price)}, Server Calculated: {type(totalPrice)}")
                print(f"Client Reported Price: {price}, Server Calculated Price: {totalPrice}")
                return Response({"state": "fail", "msg": "Purchase Failed"})
        except ObjectDoesNotExist:
                print(f"Warning, Unauthorized Item Detected.")
                return Response({"state": "fail", "msg": "ERROR, Something went wrong."})

# Management
@permission_classes([IsAuthenticated, IsAdminUser])
@api_view(["GET"])
def receipts(request):
    user = request.user
    #if not is_user_admin(user):
        #return Response({"state":"fail","msg":"ERROR 401"})
    
    receipts = Receipt.objects.all()
    products = Product.objects.all()
    product_serializer = ProductSerializer(products, many=True)  # Use the serializer
    allproducts = product_serializer.data  # Retrieve the serialized data
    payload = []
    for receipt in receipts:

        try:
            recuser = MarketUser.objects.get(id=receipt.user_id)
            products_list = json.loads(receipt.products)
            payload.append({
                "id": receipt.id,
                "price": receipt.price,
                "products": products_list,
                "recuser": {"userid": recuser.id, "username": recuser.username}
            })
        except MarketUser.DoesNotExist:
            return Response({"state": "fail", "msg": "User not found"}, status=status.HTTP_404_NOT_FOUND)
    return Response({"state":"success","payload":payload,"products":allproducts,"msg":"Success"})

@permission_classes([IsAuthenticated, IsAdminUser])
@api_view(["GET"])
def get_user_receipts(request,pk):
    try:
        ruser = MarketUser.objects.get(id=pk)
        # Assuming you have a search criteria, adjust the following line accordingly
        search_criteria = request.query_params.get('search_criteria', None)
                
        if search_criteria:
            # Use filter to get all receipts that match the search criteria
            receipts = Receipt.objects.filter(user=ruser.id, your_search_field=search_criteria)
        else:
            # If no search criteria provided, get all receipts for the user
            receipts = Receipt.objects.filter(user=ruser.id)

            products = Product.objects.all()
            pserializer = ProductSerializer(products, many=True)
                
            categories = Category.objects.all()
            cserializer = CategorySerializer(categories, many=True)

            # Combine the serialized data into a single dictionary
            combined_data = {
                'products': pserializer.data,
                'categories': cserializer.data,
            }
            serializer = ReceiptSerializer(receipts, many=True)
                
            return Response({"success": True, 'message': "Receipts Received", 'receipts': serializer.data, 'combdata':combined_data})
    except MarketUser.DoesNotExist:
        return Response({"success": False, "message": f"User {pk} not found"})
    

lockdown = False

@permission_classes([IsAuthenticated,IsAdminUser])
@api_view(["PUT"])
def setstaff(request):
    if lockdown:
        return Response({"success": False, "message": f"User not found"})
    
    try:
        data = json.loads(request.body)
        user = request.user
        if(not user.is_superuser):
            if user.is_staff:
                return Response({"success": False, "message": f"You have no access to this command."})
            else:
                 return Response({"success": False, "message": f"Something Went Wrong"})
        targetuser = data.get('userid')
        ruser = MarketUser.objects.get(id=targetuser)
        setadmin = data.get('set')
        setdata = {'is_staff':setadmin}
        serializer = UserSerializer(ruser, data=setdata, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"success": True, 'message': f"{ruser.username} Was {'Promoted To Staff' if setadmin else 'Demoted From Staff'} Refresh the page to update."})
        else:
            return Response({"success": False, 'message': "Something Went Wrong(2)"})
    except MarketUser.DoesNotExist:
        return Response({"success": False, "message": f"User  not found"})
    
@permission_classes([IsAuthenticated,IsAdminUser])
@api_view(["DELETE"])
def deleteuser(request):
    if lockdown:
        return Response({"success": False, "message": f"User not found"})
    
    try:
        data = json.loads(request.body)
        user = request.user
        if(not user.is_superuser):
            if user.is_staff:
                return Response({"success": False, "message": f"You have no access to this command."})
            else:
                 return Response({"success": False, "message": f"Something Went Wrong"})
        targetuser = data.get('userid')
        ruser = MarketUser.objects.get(id=targetuser)
        savename = ruser
        ruser.delete()
        return Response({"success": True, 'message': f"{savename} - {targetuser} Was Deleted Refresh the page to update."})

    except MarketUser.DoesNotExist:
        return Response({"success": False, "message": f"User  not found"})

@permission_classes([IsAuthenticated, IsAdminUser])
class UManagementView(APIView):
    def get(self, request):
        users = MarketUser.objects.all()
        sendusers = []
        for user in users:
            sendusers.append({
                "username": user.username,
                "id": user.id,
                "firstname": user.firstname,
                "lastname": user.lastname,
                "email": user.email,
                "gender": user.gender,
                "dob": user.date_of_birth.isoformat() if user.date_of_birth else None,
                "img": user.img.url if user.img else None,
                "is_staff": user.is_staff,
            })        
        serializer = UserSerializer(sendusers, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = UserSerializer(data=request.data, context={'user': request.user})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
   
    def put(self, request, pk):
        user = MarketUser.objects.get(pk=pk)
        serializer = UserSerializer(user, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
   
    def delete(self, request, pk):
        user = MarketUser.objects.get(pk=pk)
        user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

@permission_classes([IsAuthenticated, IsAdminUser])
class ProductsView(APIView):
    """
    This class handle the CRUD operations for MyModel
    """
    def get(self, request):

        """
        Handle GET requests to return a list of MyModel objects
        """
        products = Product.objects.all()
        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data)

    def post(self, request):
        

        """
        Handle POST requests to create a new Task object
        """

        serializer = ProductSerializer(data=request.data, context={'user': request.user})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
   
    def put(self, request, pk):
        """
        Handle PUT requests to update an existing Task object
        """
        product = Product.objects.get(pk=pk)
        serializer = ProductSerializer(product, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
   
    def delete(self, request, pk):
        """
        Handle DELETE requests to delete a Task object
        """
        product = Product.objects.get(pk=pk)
        product.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
@permission_classes([IsAuthenticated, IsAdminUser])
class PManagemetView(APIView):
    """
    This class handle the CRUD operations for MyModel
    """
    def get(self, request):
        """
        Handle GET requests to return a list of MyModel objects
        """
        products = Product.objects.all()
        serializer = ProductSerializer(products, many=True)

        categories = Category.objects.all()
        serializer2 = CategorySerializer(categories, many=True)

        merged_data = {
            "products": serializer.data,
            "categories": serializer2.data,
        }

        return Response(merged_data)


    def post(self, request):
        """
        Handle POST requests to create a new Task object
        """
        reqtype = request.data.get('type')
        if not reqtype or reqtype == None:
            return Response({"success": False, "message": f"Request Failed"})
        
        if reqtype == "product":
             
            serializer = ProductSerializer(data=request.data, context={'user': request.user})
            if serializer.is_valid():
                image_file = request.data.get('img')
                
                if image_file:
                    # Check file format and size
                    allowed_formats = ['.png']
                    max_size = 2 * 1024 * 1024  # 2MB
                    
                    if not image_file.name.lower().endswith(tuple(allowed_formats)):
                        raise ValidationError("Please upload a PNG image.")
                    
                    if image_file.size > max_size:
                        raise ValidationError("Image size must be less than 2MB.")
                    
                    request.data['img'] = SimpleUploadedFile(image_file.name, image_file.read())
                    
                serializer.save()
                return Response({"success": True, "message": f"The Product Was Added Successfully"})
                #return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response({"success": False, "message": f"The Product couldn't be added"})
        elif reqtype == "category":
            serializer = CategorySerializer(data=request.data, context={'user': request.user})
            if serializer.is_valid():
                serializer.save()
                return Response({"success": True, "message": f"The Category Was Added Successfully"})
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        #return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    def put(self, request, pk):
        """
        Handle PUT requests to update an existing product
        """
        product = Product.objects.get(pk=pk)
        serializer = ProductSerializer(product, data=request.data)
        if serializer.is_valid():
            # Handle the uploaded image file
            image_file = request.data.get('image')
            
            if image_file:
                # Check file format and size
                allowed_formats = ['.png']
                max_size = 2 * 1024 * 1024  # 2MB
                
                if not image_file.name.lower().endswith(tuple(allowed_formats)):
                    raise ValidationError("Please upload a PNG image.")
                
                if image_file.size > max_size:
                    raise ValidationError("Image size must be less than 2MB.")
                
                product.img = SimpleUploadedFile(image_file.name, image_file.read())

            serializer.save()
            # return Response(serializer.data)
            return Response({"success":True,"message":f"Product {product.name} Has been updated successfully"})
    
        return Response({"success":False,"message":"The Product was not found."})
   
    def delete(self, request, pk):
        try:
            product = Product.objects.get(pk=pk)
            
            # Check if the product's image is not the default placeholder
            if product.img.name != '/placeholder.png':
                # Delete the image file from storage
                default_storage.delete(product.img.name)

            product.delete()
            return Response({"success": True, "message": f"Product {pk} Was Deleted Successfully"})
        except Product.DoesNotExist:
            return Response({"success": False, "message": f"Product {pk} not found"})
        
#end management



@permission_classes([AllowAny])
class RegistrationView(APIView):
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        username = data.get('username')
        existing_user = MarketUser.objects.filter(username=username).exists()
        if existing_user:
            return Response({'success': False, 'message': "Username Already Used"})
        firstname = data.get('firstname')
        lastname = data.get('lastname')
        password = data.get('password')
        email = data.get('email')
        gender = data.get('gender')
        date_of_birth = data.get('date')
        try:
            validate_password(password)
        except ValidationError as e:
            return Response({'success': False, 'message': str(e)})

        
        user = MarketUser.objects.create_user(
            username=username,
            firstname=firstname,
            lastname=lastname,
            email=email,
            password=password,
            gender=gender,
            date_of_birth=date_of_birth
        )

        return Response({'success': True, 'message': f'User: {user.username} - Registration successful'})
    

from django.core.mail import send_mail

@permission_classes([AllowAny])
@api_view(["POST"])
def recovery(request):
    data = json.loads(request.body)
    email = data.get('email')
    try:
        user = MarketUser.objects.get(email=email)
        YOUR_RESET_URL = ""
        # Generate a unique token for password reset
        # You can use a library like Django Rest Framework's default token generator
        # or implement your own logic to generate a secure token
        reset_token = generate_reset_token(user)

        # Send an email with a link to the password reset view
        subject = 'Password Reset'
        message = f'Click the following link to reset your password: {YOUR_RESET_URL}?token={reset_token}'
        from_email = os.environ.get("EMAIL_HOST_USER")  # Update with your email
        recipient_list = [email]

        send_mail(subject, message, from_email, recipient_list)

        return Response({'success': True, 'message': f'Password Recovery Sent To {email}'})
    except MarketUser.DoesNotExist:
        #return Response({"success": False, "message": "Email not found"}, status=status.HTTP_404_NOT_FOUND)
        # Pretending we sent the email so that the client won't use this information against us
        return Response({'success': True, 'message': f'Password Recovery Sent To {email}'})
    except ValidationError as e:
        print(str(e))
        return Response({'success': False, 'message': "Something Went Wrong"}, status=400)
    
def generate_reset_token(user):
    # Implement your logic to generate a secure token
    # You can use Django Rest Framework's default token generator or other methods
    return 'your_generated_token'

@permission_classes([IsAuthenticated])
@api_view(["GET","PUT"])
def modprofile(request):
    if request.method == "GET":
        ruser = request.user
        # Assuming you have a search criteria, adjust the following line accordingly
        search_criteria = request.query_params.get('search_criteria', None)
        
        if search_criteria:
            # Use filter to get all receipts that match the search criteria
            receipts = Receipt.objects.filter(user=ruser.id, your_search_field=search_criteria)
        else:
            # If no search criteria provided, get all receipts for the user
            receipts = Receipt.objects.filter(user=ruser.id)

        products = Product.objects.all()
        pserializer = ProductSerializer(products, many=True)
        
        categories = Category.objects.all()
        cserializer = CategorySerializer(categories, many=True)

        # Combine the serialized data into a single dictionary
        combined_data = {
            'products': pserializer.data,
            'categories': cserializer.data,
        }
        serializer = ReceiptSerializer(receipts, many=True)
        
        return Response({"success": True, 'message': "Receipts Received", 'receipts': serializer.data, 'combdata':combined_data})
        

    elif request.method == "PUT":
        ruser = request.user
        rtype = request.data.get('rtype')

        if rtype == "newpicture":
            try:
                user = MarketUser.objects.get(id=ruser.id)
                if ruser.id != user.id:
                    return Response({"success":False,'message':"Something Went Wrong(1)"})
                
                image_file = request.data.get('img')
                    
                if image_file:
                    # Check file format and size
                    allowed_formats = ['.png']
                    max_size = 2 * 1024 * 1024  # 2MB
                        
                    if not image_file.name.lower().endswith(tuple(allowed_formats)):
                        raise ValidationError("Please upload a PNG image.")
                        
                    if image_file.size > max_size:
                        raise ValidationError("Image size must be less than 2MB.")
                    
                    # Use the serializer to update the user instance
                    data = {'img': SimpleUploadedFile(image_file.name, image_file.read(), content_type='image/png')}
                    serializer = UserSerializer(user, data=data, partial=True)
                    if serializer.is_valid():
                        serializer.save()
                        return Response({"success": True, 'message': "Picture Changed Successfully", 'picname':image_file.name or None})
                    else:
                        return Response({"success": False, 'message': "Something Went Wrong"})
                        
                
                return Response({"success":False,'message':"Image Was Not Found."})
            except MarketUser.DoesNotExist:
                return Response({'success': True, 'message': f'Something Went Wrong'})
            except ValidationError as e:
                print(str(e))
                return Response({'success': False, 'message': "Something Went Wrong"}, status=400)
        elif rtype == "newname":
            try:
                user = MarketUser.objects.get(id=ruser.id)
                if ruser.id != user.id:
                    return Response({"success":False,'message':"Something Went Wrong(1)"})
                
                firstname = request.data.get('firstname')
                lastname = request.data.get('lastname')
                    
                if firstname and lastname:

                    if user.firstname == firstname and user.lastname == lastname:
                        return Response({"success": False, 'message':"Your New Name cant be the same as your current name."})
                    # Check file format and size

                    # Use the serializer to update the user instance
                    data = {'firstname':firstname,'lastname':lastname}
                    serializer = UserSerializer(user, data=data, partial=True)
                    if serializer.is_valid():
                        serializer.save()
                        return Response({"success": True, 'message': f"Name Changed Successfully To {firstname} {lastname}","firstname":firstname,"lastname":lastname})
                    else:
                        return Response({"success": False, 'message': "Something Went Wrong(2)"})
                        
                return Response({"success":False,'message':"Firstname or Lastname weren't specified"})
            except MarketUser.DoesNotExist:
                return Response({'success': True, 'message': f'Something Went Wrong(3)'})
            except ValidationError as e:
                print(str(e))
                return Response({'success': False, 'message': "Something Went Wrong(4)"}, status=400)
        else:
            return Response({"success":False,'message':"Something Went Wrong(3)"})
            
