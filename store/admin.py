from django.contrib import admin

from .models import (
    CommunityHighlight, HighlightEngagement, HighlightComment,
    DiscountVoucher, SellerHighlightGoal,
)


@admin.register(SellerHighlightGoal)
class SellerHighlightGoalAdmin(admin.ModelAdmin):
    list_display = ("seller", "points_goal", "discount_percent", "voucher_validity_days", "is_active")
    list_filter = ("is_active",)
    search_fields = ("seller__store_name",)


class HighlightCommentInline(admin.TabularInline):
    model = HighlightComment
    extra = 0
    readonly_fields = ("user", "body", "created_at")


@admin.register(CommunityHighlight)
class CommunityHighlightAdmin(admin.ModelAdmin):
    list_display = ("title", "buyer", "product", "seller", "total_points",
                    "points_goal", "reward_unlocked", "is_approved", "created_at")
    list_filter = ("reward_unlocked", "is_approved", "is_active", "media_type")
    search_fields = ("title", "body", "buyer__username", "product__name")
    readonly_fields = ("total_points", "like_count", "comment_count",
                       "share_count", "reward_unlocked", "unlocked_at")
    inlines = [HighlightCommentInline]
    actions = ["recalculate_points"]

    @admin.action(description="Recalculate points and issue any earned voucher")
    def recalculate_points(self, request, queryset):
        issued = 0
        for highlight in queryset:
            highlight.recalculate()
            if highlight.maybe_unlock_reward():
                issued += 1
        self.message_user(request, f"Recalculated {queryset.count()}; {issued} voucher(s) issued.")


@admin.register(HighlightEngagement)
class HighlightEngagementAdmin(admin.ModelAdmin):
    list_display = ("highlight", "user", "action", "points", "created_at")
    list_filter = ("action",)
    search_fields = ("user__username", "highlight__title")


@admin.register(DiscountVoucher)
class DiscountVoucherAdmin(admin.ModelAdmin):
    list_display = ("code", "buyer", "seller", "discount_percent", "is_used", "expires_at", "created_at")
    list_filter = ("is_used", "discount_percent")
    search_fields = ("code", "buyer__username", "seller__store_name")
    readonly_fields = ("code", "created_at")
