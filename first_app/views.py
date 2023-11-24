from django.shortcuts import render
from django.http import HttpResponse
from first_app.models import  File, CSVFile
from django.http import JsonResponse
# from .models import Topic
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from rest_framework.decorators import api_view
import pandas as pd
import numpy as np
from django.http import JsonResponse
from ctgan import CTGAN
import json
from django.core.exceptions import ObjectDoesNotExist
from table_evaluator import TableEvaluator
import matplotlib
import matplotlib.pyplot as plt
import io
import os

matplotlib.use('Agg')
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# from django.core.files.base import ContentFile
# from django.core.files.storage import FileSystemStorage 

# Create your views here.

@csrf_exempt
@require_POST
def main(request):
    try:
        file= request.FILES['file']
        name=request.POST.get('name')
        print("name = ",name)

        # Specify the directory where you want to save the file
        save_directory = 'first_app/user_files'

        # Create the directory if it doesn't exist
        if not os.path.exists(save_directory):
            os.makedirs(save_directory)

        # Use os.path.join to create the full path including the filename
        file_path = os.path.join(save_directory, f"{name}.csv")

        # Save the file with the given name in the specified directory
        with open(file_path, 'wb') as destination:
            for chunk in file.chunks():
                destination.write(chunk)

        obj= File.objects.create(file = file)
        df= pd.read_csv(obj.file)
        des= df.describe()
        catObj= np.array(df.select_dtypes("object").columns)
        ctgan = CTGAN(verbose=True)
        ctgan.fit(df, catObj, epochs = 2)
        ctgan.save(f"first_app/models/{name}_model.pkl")

        # samples = ctgan.sample(10)

        # samples_2d_array = samples.values.tolist()
        # print(samples_2d_array)        
        return JsonResponse(
            {
                'res':'Model trained successfully',
                # 'data': samples_2d_array
            }
        , status=200)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status= 500)


@csrf_exempt
@require_POST
def generate_data(request):
    try:
        data = json.loads(request.body)
        n_rows = int(data.get('n_rows', 10))
        model_name = data.get('model_name')  # Assuming you pass the model name as a parameter
        if not model_name:
            return JsonResponse({'error': 'Model name not provided'}, status=400)
        model_path = f"first_app/models/{model_name}_model.pkl"
        
        # Load the pre-trained model
        ctgan = CTGAN.load(model_path)

        samples = ctgan.sample(n_rows)
        samples.to_csv(f"first_app/generated_data/{model_name}.csv")
        print(samples)
        samples_2d_array = [samples.columns.tolist()] + samples.values.tolist()
        print(samples_2d_array)
        return JsonResponse({'res': samples_2d_array}, status=200)
    except ObjectDoesNotExist:
        return JsonResponse({'error': 'Model not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@api_view(['POST'])
def sample_model(request):
    try:
        data = json.loads(request.body)
        param1= request.query_params.get('model')
        n_rows = int(data.get('n_rows', 10))

        if not param1:
            return JsonResponse({'error': 'model name not provided'}, status= 400)
        # if param1!='adult' or param1!='company':
        #     return JsonResponse({'error': 'Invalid model name'}, status= 400)
        path= f"first_app/pretrained_models/{param1}.pkl"
        ctgan= CTGAN.load(path)
        samples= ctgan.sample(n_rows)
        samples.to_csv(f"first_app/generated_data/{param1}.csv")
        samples_2d_array = [samples.columns.tolist()] + samples.values.tolist()

        return JsonResponse({ 'data': samples_2d_array }, status= 200)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@api_view(['POST'])
def generate_report(request):
    try:

        data= json.loads(request.body)
        file_name= data.get('file_name')

        # Construct absolute paths
        file_path = os.path.join(base_dir, "first_app", "user_files", f"{file_name}.csv")
        new_data_path = os.path.join(base_dir, "first_app", "generated_data", f"{file_name}.csv")
        print(file_path)
        print(new_data_path)
        # Check if files exist
        if not os.path.exists(file_path) or not os.path.exists(new_data_path):
            return JsonResponse({'error': 'File not found'}, status=404)

        df= pd.read_csv(file_path)
        new_data= pd.read_csv(new_data_path)
        new_data= new_data.drop(new_data.columns[0], axis=1)
        table_evaluator = TableEvaluator(df,new_data)

        # Generate the plot using a method from TableEvaluator (replace with actual method name)
        # plot = table_evaluator.generate_plot()

        # Save the plot as a PNG file
        # image_path = os.path.join(base_dir, "first_app", "plots", "plot.png")
        # plot.savefig(image_path, format='png')

        # plt.savefig('myfig')
        print(table_evaluator)
        table_evaluator.visual_evaluation()
        return JsonResponse({'res':table_evaluator}, status=200)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)