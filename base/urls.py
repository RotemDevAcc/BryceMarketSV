from django.urls import path, include
from . import views
from .views import ProductsView, PManagemetView, UManagementView, RegistrationView
urlpatterns = [
    path('', views.index),
    path('products/', ProductsView.as_view(), name='product-list'),
    path('productslist/',views.productlist),
    path('getreceipts/', views.receipts),

    #Management
    path('pmanagement/', PManagemetView.as_view(), name='product-manage'),
    path('pmanagement/<int:pk>/', PManagemetView.as_view(), name='product-managepk'),
    path('umanagement/', UManagementView.as_view(), name='user-manage'),
    path('umanagement/receipts/<int:pk>/',views.get_user_receipts, name='user-manage-receipts'),
    path('umanagement/set/', views.setstaff,name='set-staff'),
    path('umanagement/delete/', views.deleteuser,name='delete-user'),

    #Users
    path('login/', views.MyTokenObtainPairView.as_view()),
    path('recovery/', views.recovery),
    path('register/', RegistrationView.as_view(), name='register'),
    path('profile/',views.modprofile, name="profile-modify"),


    # path('purchase/',views.purchase)
]
