from .models import Category

def askgt_categories(request):
    """AskGT kategorilerini template context'e ekle"""
    categories = Category.objects.filter(is_active=True).order_by('order', 'name')
    
    return {
        'askgt_categories': categories,
        'askgt_categories_count': categories.count(),
    }
