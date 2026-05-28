import azure.functions as func
import logging
import json
import os
import time
import hmac
import hashlib
import base64
import requests
from urllib.parse import quote
from azure.cosmos import CosmosClient
from azure.storage.blob import BlobServiceClient


app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


def enviar_notificacion_push(id_pedido, url_foto=None):
    """Método REST: Envía la notificación push directo a Azure Notification Hubs incluyendo la evidencia"""
    try:
        hub_name = os.environ.get("NH_NAME")
        connection_string = os.environ.get("NH_CONNECTION_STRING")
        
        if not connection_string or not hub_name:
            logging.error("Faltan variables de entorno para el Notification Hub")
            return False

        # 1. Parsear la cadena de conexión
        parts = dict(item.split('=', 1) for item in connection_string.split(';'))
        endpoint = parts['Endpoint'].replace('sb://', 'https://')
        sas_key_name = parts['SharedAccessKeyName']
        sas_key_value = parts['SharedAccessKey']
        
        # 2. Generar el Token de Seguridad (SAS Token)
        uri = f"{endpoint}{hub_name}/messages".lower()
        target_uri = quote(uri, safe='')
        expiry = int(time.time() + 3600)
        to_sign = f"{target_uri}\n{expiry}"
        signature = base64.b64encode(
            hmac.new(sas_key_value.encode('utf-8'), to_sign.encode('utf-8'), hashlib.sha256).digest()
        ).decode('utf-8')
        auth_header = f"SharedAccessSignature sr={target_uri}&sig={quote(signature)}&se={expiry}&skn={sas_key_name}"

        # 3. Preparar el mensaje para Firebase (FCM v1) con la URL del Blob Storage
        # El estándar fcmv1 requiere estructurar el JSON bajo la llave "message" -> "data"
        payload = {
            "message": {
                "notification": {
                    "title": "¡Tu pedido va en camino!",
                    "body": f"El repartidor inició el viaje para tu pedido #{id_pedido}"
                },
                "data": {
                    "id_pedido": str(id_pedido),
                    "estado": "en camino",
                    "urlEvidencia": str(url_foto) if url_foto else ""  # <- Aquí viaja el link del Blob de parche
                }
            }
        }

        # 4. Enviar la petición POST al Gateway de Azure
        headers = {
            "Authorization": auth_header,
            "Content-Type": "application/json;charset=utf-8",
            "ServiceBusNotification-Format": "fcmv1" # Indica a Azure que el payload usa la sintaxis FCM v1
        }
        
        url = f"{uri}?api-version=2015-01"
        response = requests.post(url, json=payload, headers=headers)
        
        if response.status_code == 201:
            logging.info("Notificación push despachada con éxito a través de Azure")
            return True
        else:
            logging.error(f"Azure NH rechazó la petición. Código: {response.status_code}, Respuesta: {response.text}")
            return False

    except Exception as e:
        logging.error(f"Fallo crítico en el envío: {str(e)}")
        return False


def get_container():
    conn_str = os.environ.get("COSMOS_CONNECTION_STRING")
    if not conn_str:
        # Esto te ayudará a saber si el problema es el archivo local.settings.json
        raise ValueError("Error: La variable COSMOS_CONNECTION_STRING no está definida.")
    
    client = CosmosClient.from_connection_string(conn_str)
    database = client.get_database_client("rapidgodb")
    return database.get_container_client("pedidos")

@app.route(route="registrar_pedido", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
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
            "id": str(id_pedido),
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


@app.route(route="consultar_historial", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def consultar_historial(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Consultando historial de pedidos limpio...')
    try:
        container = get_container()
        pedidos_raw = list(container.read_all_items())
        
        pedidos_limpios = []
        
        for pedido in pedidos_raw:
            pedido_formateado = {
                "id": pedido.get("id"),
                "id_pedido": pedido.get("id_pedido"),
                "producto": pedido.get("producto"),
                "cantidad": pedido.get("cantidad"),
                "estado": pedido.get("estado"),
                "fotoUrl": pedido.get("fotoUrl", "") 
            }
            pedidos_limpios.append(pedido_formateado)
            
        return func.HttpResponse(
            json.dumps(pedidos_limpios), 
            mimetype="application/json", 
            status_code=200
        )
        
    except Exception as e:
        logging.error(f"Error en consultar_historial: {str(e)}")
        return func.HttpResponse(f"Error: {str(e)}", status_code=500)


@app.route(route="actualizar_estado", methods=["PUT"], auth_level=func.AuthLevel.ANONYMOUS)
def actualizar_estado(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Iniciando actualización de pedido con evidencia multimedia...')
    try:
        container = get_container()
        
        id_pedido = req.form.get('id_pedido')
        nuevo_estado = req.form.get('estado')

        if not id_pedido or not nuevo_estado:
            return func.HttpResponse("Faltan datos obligatorios (id_pedido o estado)", status_code=400)

        url_evidencia = None

        if nuevo_estado.lower() == "en camino":
            imagen_file = req.files.get('evidencia')
            
            if imagen_file:
                archivo_bytes = imagen_file.stream.read()
                
                extension = imagen_file.filename.split('.')[-1] if '.' in imagen_file.filename else 'png'
                nombre_blob = f"pedido_{id_pedido}.{extension}"
                
                connection_string = os.environ["AZURE_STORAGE_CONNECTION_STRING"]
                blob_service_client = BlobServiceClient.from_connection_string(connection_string)
                blob_client = blob_service_client.get_blob_client(container="evidencias", blob=nombre_blob)
                
                blob_client.upload_blob(archivo_bytes, overwrite=True)
                
                url_evidencia = blob_client.url
                logging.info(f"Imagen subida exitosamente. URL: {url_evidencia}")
            else:
                return func.HttpResponse("Se requiere adjuntar un archivo en el campo 'evidencia' cuando el estado es 'en camino'", status_code=400)

        patch_ops = [{'op': 'replace', 'path': '/estado', 'value': nuevo_estado}]
        
        if url_evidencia:
            patch_ops.append({'op': 'set', 'path': '/fotoUrl', 'value': url_evidencia})

        container.patch_item(
            item=str(id_pedido),
            partition_key=str(id_pedido),
            patch_operations=patch_ops
        )

        # 4. LÓGICA DE NOTIFICACIÓN (Pasamos la URL de la foto para que viaje en la push)
        notificacion_ok = False
        if nuevo_estado.lower() == "en camino":
            # Modifica tu función interna para que reciba la URL de la evidencia si la necesitas en FCM
            notificacion_ok = enviar_notificacion_push(id_pedido, url_evidencia)

        return func.HttpResponse(
            json.dumps({
                "mensaje": "Pedido actualizado con evidencia",
                "notificacion_enviada": notificacion_ok,
                "fotoUrl": url_evidencia
            }),
            mimetype="application/json",
            status_code=200
        )

    except Exception as e:
        logging.error(f"Error: {str(e)}")
        return func.HttpResponse(f"Error en servidor: {str(e)}", status_code=500)
