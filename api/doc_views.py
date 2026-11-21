from django.shortcuts import render


def api_docs_view(request):
    return render(request, 'api/docs.html')
