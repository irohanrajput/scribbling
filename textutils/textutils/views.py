from django.http import HttpResponse
from django.shortcuts import render


def index(request):
    return render(request, 'index.html')

def contact_us(request):
    return render(request, 'contact_us.html')

def about(request):
    return render(request, 'about.html')


def analyze(request):
    # getting the text and the putting it in a variable

    newtext = (request.GET.get('text', 'default'))
    removepunc = request.GET.get('removepunc', 'off')
    upper = request.GET.get('uprcase', 'off')
    nlr = request.GET.get('newlineremover', 'off')
    lower = request.GET.get('lwrcase', 'off')


    print (f'removepunc:{removepunc}') # true/false
    print (f'Input Text:{newtext}')
    print (f'upper:{upper}')
    print (f'nlr:{nlr}')
    print (f'lower:{lower}')

    puncs = '''!"#$%&'()*+,-./:;<=>?@[\]^_`{|}~'''
    analyzed = newtext  # Start with the original text


    # if removepunc == 'on':
    #     analyzed = ""
    #     for char in newtext:
    #         if char not in puncs:
    #             analyzed += char

    if removepunc == 'on':
        analyzed = ''.join(char for char in analyzed if char not in puncs)
 
    if upper == 'on':
        analyzed = analyzed.upper()

    if lower == 'on':
        analyzed = analyzed.lower()

    if nlr == 'on':
        analyzed = analyzed.replace('\n','')

    
    params = {'purpose': 'is analyzed and modified as per requested', 'analyzed_text': analyzed}
    
    return render(request, 'analyze.html', params)
    



     
    
    