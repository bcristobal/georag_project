import os
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from dotenv import load_dotenv
from pydantic import BaseModel

# Cargar variables de entorno desde el archivo .env
load_dotenv()

ZAI_BASE_URL = os.getenv("ZAI_BASE_URL")
ZAI_API_KEY = os.getenv("ZAI_API_KEY")

# Crear un modelo de Pydantic para representar el output esperado del agente que será una lista de tareas que el agente debe realizar para ayudar al usuario a desarrollar.
class AgentTasks(BaseModel):
    tasks: list[str]


# Validación rápida para asegurar que la API key se cargó correctamente
if not ZAI_API_KEY:
    raise ValueError("⚠️ No se encontró ZAI_API_KEY. Verifica tu archivo .env.")

# Configurar el modelo GLM-4.7-Flash usando el proveedor de OpenAI
model = OpenAIChatModel(
    'glm-4.7-flash',
    provider=OpenAIProvider(
        base_url=ZAI_BASE_URL, 
        api_key=ZAI_API_KEY
    ),
)

system_prompt = 'You are a helpful AI assistant helping users with their tasks.'

# Crear el agente de Pydantic AI
agent = Agent(
    model,
    system_prompt=system_prompt,
    #output_type=AgentTasks,
    )

def main():
    print("Iniciando prueba de conexión con z.ai (GLM-4.7-Flash)...")
    
    # Mensaje de prueba para verificar que el modelo razona y responde
    # test_message = "Hola. Por favor confirma que estás conectado respondiendo con un simple '¡Conexión exitosa, listo para ayudar con Pydantic AI!'."
    test_message = """Kaixo, non dago Andra Mari Zurianren Plaza?"""

    try:
        # Ejecutar el agente de forma síncrona
        result = agent.run_sync(test_message)
        
        print("\n✅ Conexión establecida correctamente.")
        print("-" * 40)
        print(f"Respuesta del Agente:\n{result.output}")
        print("-" * 40)
        
    except Exception as e:
        print(f"\n❌ Ocurrió un error al intentar conectar: {e}")

if __name__ == "__main__":
    main()