import google.generativeai as genai
genai.configure(api_key="AIzaSyA1gS3d3MvHJ-kUnK7CYsXTY6MHPHpzN_0")

for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(m.name)