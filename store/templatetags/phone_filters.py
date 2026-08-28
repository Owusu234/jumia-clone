from django import template

register = template.Library()

@register.filter
def format_whatsapp_phone(phone):
    """Format phone number for WhatsApp wa.me links by removing +, spaces, dashes, parentheses"""
    if not phone:
        return ""
    # Convert to string and clean
    phone_str = str(phone).strip()
    # Remove common formatting characters
    cleaned = phone_str.replace('+', '').replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
    return cleaned