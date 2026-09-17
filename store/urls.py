from django.urls import path
from . import views

app_name = "store"

urlpatterns = [
   
    # ==================== CORE STOREFRONT ====================
    
    path("", views.home, name="home"),
    path("wishlist/", views.wishlist, name="wishlist"),
    path("api/wishlist/products/", views.wishlist_products_api, name="wishlist_products_api"),
    path("product/<slug:slug>/", views.product_detail, name="product_detail"),
    path("seller/<int:seller_id>/", views.seller_store, name="seller_store"),
    path("seller/<int:seller_id>/follow/", views.toggle_follow, name="toggle_follow"),
    path("complete-profile/", views.complete_profile, name="complete_profile"),
    path("support/", views.contact_support, name="contact_support"),
    path("api/regions/", views.get_regions_by_country, name="api_regions"),
    path("api/save-delivery-info/", views.save_delivery_info, name="save_delivery_info"),
    path('admin/notifications/read/', views.mark_notifications_read, name='mark_notifications_read'),
    path('notifications/read/', views.mark_user_notifications_read, name='mark_user_notifications_read'),
    path("api/chatbot/recommend/", views.chatbot_recommend, name="chatbot_recommend"),
    # ==================== CART (UUID Compatible) ====================

    path('cart/update/', views.update_cart, name='update_cart'),
    path('add-to-cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/', views.cart, name='cart'),
    path('cart/remove/<int:product_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/share/', views.share_cart, name='share_cart'),
    path('cart/shared/<uuid:token>/', views.shared_cart, name='shared_cart'),
    path('cart/shared/<uuid:token>/purchase/<str:action>/', views.start_shared_cart_purchase, name='start_shared_cart_purchase'),
    path('cart/item/share-toggle/', views.toggle_cart_item_shared, name='toggle_cart_item_shared'),
    path('cart/shared/item/<int:item_id>/add/', views.add_shared_item_to_cart, name='add_shared_item_to_cart'),
    path('cart/shared/item/<int:item_id>/purchase/<str:action>/', views.start_linked_cart_purchase, name='start_linked_cart_purchase'),
    path('cart/stop-sharing/', views.stop_sharing_cart, name='stop_sharing_cart'),
    path('cart/link/invite/', views.invite_to_cart, name='invite_to_cart'),
    path('cart/link/accept/<uuid:token>/', views.accept_invite_via_email, name='accept_invite_via_email'),
    path('cart/link/<int:invite_id>/cancel/', views.cancel_cart_invite, name='cancel_cart_invite'),
    path('cart/link/<int:invite_id>/<str:action>/', views.respond_cart_invite, name='respond_cart_invite'),
    path('cart/', views.cart_view, name='cart'),
    # ==================== IN-SITE CHAT & INVOICES ====================

    path('chat/', views.chat_inbox, name='chat_inbox'),
    path('chat/start/<int:product_id>/', views.start_conversation, name='start_conversation'),
    path('chat/<int:conversation_id>/', views.chat_thread, name='chat_thread'),
    path('chat/<int:conversation_id>/messages/', views.chat_messages, name='chat_messages'),
    path('chat/<int:conversation_id>/send/', views.chat_send, name='chat_send'),
    path('chat/<int:conversation_id>/delete/', views.chat_delete_conversation, name='chat_delete_conversation'),
    path('chat/<int:conversation_id>/message/<int:message_id>/delete/', views.chat_delete_message, name='chat_delete_message'),
    path('chat/<int:conversation_id>/location/', views.chat_share_location, name='chat_share_location'),
    path('chat/<int:conversation_id>/invoice/', views.issue_invoice, name='issue_invoice'),
    path('invoice/<int:invoice_id>/cancel/', views.cancel_invoice, name='cancel_invoice'),
    path('invoice/<int:invoice_id>/decline/', views.decline_invoice, name='decline_invoice'),
    path('invoice/<int:invoice_id>/pay/', views.pay_invoice, name='pay_invoice'),

    path('admin/seller/<int:seller_id>/approve/', views.approve_seller, name='approve_seller'),
    path('admin/seller/<int:seller_id>/reject/', views.reject_seller, name='reject_seller'),
    path('admin/seller/<int:seller_id>/application/', views.seller_application_detail, name='seller_application_detail'),
   
    # ==================== PAYSTACK CHECKOUT & RECEIPTS ====================

    path("checkout/", views.checkout, name="checkout"),
    path("checkout/initialize/", views.initialize_paystack_payment, name="initialize_paystack"),
    path("checkout/verify/", views.verify_paystack_payment, name="verify_paystack"),
    path('checkout/callback/', views.paystack_callback, name='paystack_callback'),
    
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
    # Alias: superuser_dashboard.html links to this name specifically.
    path("admin/delete-user/<int:user_id>/", views.admin_remove_user, name="delete_user"),
    path("admin/update-price/<int:product_id>/", views.admin_update_price, name="admin_update_price"),

    # Admin Analytics & Orders

    path("admin/analytics/", views.admin_analytics, name="admin_analytics"),
    path("admin/orders/", views.admin_orders, name="admin_orders"),
    path("admin/orders/<int:order_id>/update-status/", views.admin_update_order_status, name="admin_update_order_status"),
    path("order/<int:order_id>/update-status/", views.update_order_status, name="update_order_status"),
    path("analytics/", views.analytics_dashboard, name="analytics_dashboard"),
    path("api/analytics/", views.analytics_api, name="analytics_api"),
    path("api/seller/daily-sales/", views.seller_daily_sales_api, name="seller_daily_sales_api"),

    # ==================== COMMUNITY HIGHLIGHTS ====================

    path("community/", views.community_highlights, name="community_highlights"),
    path("community/<int:highlight_id>/", views.highlight_detail, name="highlight_detail"),
    path("community/post/", views.create_highlight, name="create_highlight"),
    path("community/<int:highlight_id>/edit/", views.edit_highlight, name="edit_highlight"),
    path("community/<int:highlight_id>/delete/", views.delete_highlight, name="delete_highlight"),

    # Engagement endpoints (AJAX) — like +1, comment +2, share +3
    path("community/<int:highlight_id>/like/", views.toggle_highlight_like, name="toggle_highlight_like"),
    path("community/<int:highlight_id>/comment/", views.add_highlight_comment, name="add_highlight_comment"),
    path("community/<int:highlight_id>/share/", views.share_highlight, name="share_highlight"),

    # Seller goal + buyer voucher wallet
    path("seller/highlight-goal/", views.set_highlight_goal, name="set_highlight_goal"),
    path("vouchers/", views.my_vouchers, name="my_vouchers"),
    path("api/voucher/validate/", views.validate_voucher, name="validate_voucher"),
]
