from django.urls import path
from . import views

app_name = "store"

urlpatterns = [
   
    # ==================== CORE STOREFRONT ====================
    
    path("", views.home, name="home"),
    path("product/<slug:slug>/", views.product_detail, name="product_detail"),
    # path("complete-profile/", views.complete_profile, name="complete_profile"),
    path("api/regions/", views.get_regions_by_country, name="api_regions"),
    path('admin/notifications/read/', views.mark_notifications_read, name='mark_notifications_read'),
   
    # ==================== CART (UUID Compatible) ====================

    path('cart/update/', views.update_cart, name='update_cart'),
    path('add-to-cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/', views.cart, name='cart'),
    path('cart/remove/<int:product_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/', views.cart_view, name='cart'),
    path('admin/seller/<int:seller_id>/approve/', views.approve_seller, name='approve_seller'),
    path('admin/seller/<int:seller_id>/reject/', views.reject_seller, name='reject_seller'),
    path('admin/seller/<int:seller_id>/application/', views.seller_application_detail, name='seller_application_detail'),
   
    # ==================== PAYSTACK CHECKOUT & RECEIPTS ====================

    path("checkout/", views.checkout, name="checkout"),
    path("checkout/initialize/", views.initialize_paystack_payment, name="initialize_paystack"),
    path("checkout/verify/", views.verify_paystack_payment, name="verify_paystack"),

    
    # ==================== USER ORDERS ====================

    path("orders/", views.order_history, name="order_history"),
    path("order/receipt/<int:order_id>/", views.order_receipt, name="order_receipt"),
    path("order/success/<int:order_id>/", views.order_success, name="order_success"),
    path("orders/", views.user_orders, name="user_orders"),
    path('order/<int:order_id>/cancel/', views.cancel_order, name='cancel_order'),
  
    # ==================== AUTH & USER ====================

    path("register/", views.register, name="register"),
    path("profile/", views.profile, name="profile"),
    path("oauth/callback/", views.oauth_callback, name="oauth_callback"),
    path("register/", views.register, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path('password/forgot/', views.forgot_password, name='forgot_password'),
    path('password/reset/', views.password_reset, name='password_reset'),
    path('api/reset-password/', views.api_reset_password, name='api_reset_password'),

    # ==================== SELLER PORTAL ====================

    path("seller/signup/", views.seller_signup, name="seller_signup"),    
    path("seller/dashboard/", views.seller_dashboard, name="seller_dashboard"),
    path("seller/analytics/", views.seller_analytics, name="seller_analytics"),
    path("seller/upload/", views.upload_product, name="upload_product"),
    path("seller/delete-product/<int:product_id>/", views.delete_product, name="delete_product"),
    path("order/<int:order_id>/track/", views.track_order, name="track_order"),
    # ==================== ADMIN DASHBOARD ====================
    path("admin/dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("admin/add-user/", views.admin_add_user, name="admin_add_user"),
    path("admin/remove-user/<int:user_id>/", views.admin_remove_user, name="admin_remove_user"),
    path("admin/update-price/<int:product_id>/", views.admin_update_price, name="admin_update_price"),

    # Admin Analytics & Orders

    path("admin/analytics/", views.admin_analytics, name="admin_analytics"),
    path("admin/orders/", views.admin_orders, name="admin_orders"),
    path("admin/orders/<int:order_id>/update-status/", views.admin_update_order_status, name="admin_update_order_status"),
    path("order/<int:order_id>/update-status/", views.update_order_status, name="update_order_status"),
    path("analytics/", views.analytics_dashboard, name="analytics_dashboard"),
    path("api/analytics/", views.analytics_api, name="analytics_api"),
    path("api/seller/daily-sales/", views.seller_daily_sales_api, name="seller_daily_sales_api"),
]