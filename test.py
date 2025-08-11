from transformers import pipeline

# Cargar el modelo de GPT-Neo desde Hugging Face
chatbot = pipeline("text-generation", model="EleutherAI/gpt-neo-1.3B")

def generar_respuesta_ia(mensaje):
    # Generar respuesta utilizando el modelo GPT-Neo
    respuesta = chatbot(mensaje, max_length=100, num_return_sequences=1)
    return respuesta[0]['generated_text']

# Ejemplo de uso:
mensaje = "¿Cómo puedo integrar un chatbot con IA?"
respuesta_ia = generar_respuesta_ia(mensaje)
print(respuesta_ia)
