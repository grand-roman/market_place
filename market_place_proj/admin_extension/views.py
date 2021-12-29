from django.core.cache import cache
from django.shortcuts import render

from admin_extension.forms import ImportFileForm
from admin_extension.models import Files
from admin_extension.tasks import import_file


def admin_settings(request):
    data = {'data': 'data'}
    if request.method == 'POST':
        if request.POST.get('full'):
            cache.clear()
        if request.POST.get('main'):
            keys = ['category', 'slider_stocks', 'hot_product']
            cache.delete_many(keys)
        if request.POST.get('category'):
            key = 'category'
            cache.delete_many(key)
        if request.POST.get('goods'):
            key = ''
            cache.delete_many(key)
        if request.POST.get('orders'):
            key = ''
            cache.delete_many(key)
        if request.POST.get('discount'):
            key = ''
            cache.delete_many(key)
    return render(request, 'admin/admin_settings.html', data)


def import_files(request):
    if request.method == 'POST':
        form = ImportFileForm(request.POST, request.FILES)
        if form.is_valid():
            files = request.FILES.getlist('files')
            for file in files:
                Files.objects.create(file_start=file)
            email = form.cleaned_data.get('email')
            import_file.delay(email=email)
    else:
        form = ImportFileForm()
    return render(request, 'admin/import_goods.html', {'form': form})
