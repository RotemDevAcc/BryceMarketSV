from django.contrib import admin
from .models import Product, Category, Receipt, MarketUser
# Register your models here.



admin.site.register([MarketUser, Product, Category, Receipt])
