import azure.functions as func
import logging
import json
import os
from azure.cosmos import CosmosClient

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

# Usamos una función para obtener el cliente de forma segura
def get_container():
    conn_str = os.environ.get("COSMOS_CONNECTION_STRING")
    if not conn_str:
        # Esto te ayudará a saber si el problema es el archivo local.settings.json
        raise ValueError("Error: La variable COSMOS_CONNECTION_STRING no está definida.")
    
    client = CosmosClient.from_connection_string(conn_str)
    database = client.get_database_client("RapidGoDB")
    return database.get_container_client("Pedidos")

@app.route(route="registrar_pedido", methods=["POST"])
def registrar_pedido(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Registrando pedido en Cosmos DB...')
    try:
        container = get_container() # Obtener el contenedor aquí
        req_body = req.get_json()
        
        # Verificación básica de datos recibidos
        id_pedido = req_body.get('id_pedido')
        if not id_pedido:
            return func.HttpResponse("Error: Falta id_pedido en el JSON", status_code=400)

        nuevo_pedido = {
            "id": str(id_pedido), # Cosmos requiere que el ID sea un STRING
            "id_pedido": id_pedido,
            "producto": req_body.get('producto'),
            "cantidad": req_body.get('cantidad'),
            "estado": "confirmado"
        }

        container.create_item(body=nuevo_pedido)

        return func.HttpResponse(
            json.dumps({"status": "Éxito", "data": nuevo_pedido}), 
            mimetype="application/json", 
            status_code=201
        )
    except Exception as e:
        logging.error(f"Error detallado: {str(e)}")
        return func.HttpResponse(f"Error: {str(e)}", status_code=500)


@app.route(route="consultar_historial", methods=["GET"])
def consultar_historial(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Consultando historial de pedidos...')
    try:
        container = get_container()
        pedidos = list(container.read_all_items())
        return func.HttpResponse(json.dumps(pedidos), mimetype="application/json", status_code=200)
    except Exception as e:
        return func.HttpResponse(f"Error: {str(e)}", status_code=500)


