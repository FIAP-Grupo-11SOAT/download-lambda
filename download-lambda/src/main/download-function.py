import os
import json
import logging
import boto3
import urllib.request
import base64

logger = logging.getLogger()
logger.setLevel(logging.INFO)

S3_BUCKET = os.environ.get('BUCKET')
TABLE_NAME = os.environ.get('TABLE')

def lambda_handler(event, context):
    """Handler Lambda para gerar URL de download (presigned).

    Espera `pathParameters.filename` contendo o nome do ZIP em `outputs/`.
    Retorna JSON com `download_url` em português.
    """

    if not S3_BUCKET:
        return responder(500, {'success': False, 'message': 'Variável de ambiente BUCKET não configurada'})

    if not TABLE_NAME:
        return responder(500, {'success': False, 'message': 'Variável de ambiente TABLE não configurada'})

    record_id_raw = obter_id_registro(event)
    if not record_id_raw:
        return responder(400, {'success': False, 'message': 'Parâmetro id/filename ausente'})

    user_email = validar_jwt(id_token)

    try:
        # Extrai o upload_id do parâmetro original e usa o email autenticado
        _, upload_id = record_id_raw.rsplit('_', 1)
        record_id = f"{user_email}_{upload_id}"
    except ValueError:
        return responder(400, {'success': False, 'message': 'Formato de ID inválido'})

    if not user_email:
        return responder(401, {'success': False, 'message': 'Falha na autenticação'})

    logger.info(f"Iniciando busca de download para o ID: {record_id}")

    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(TABLE_NAME)

    try:
        item = buscar_registro(table, record_id)
    except Exception as e:
        logger.exception('Erro ao consultar DynamoDB')
        return responder(500, {'success': False, 'message': 'Erro ao consultar banco: ' + str(e)})

    if not item:
        return responder(404, {'success': False, 'message': 'Registro não encontrado'})

    s3_key = item.get('s3_key')
    status = item.get('status')
    if not s3_key:
        return responder(400, {'success': False, 'message': f'Registro encontrado com status {status}, sem arquivo disponível ainda'})

    url = gerar_url_presignada(s3_key)
    if not url:
        logger.exception('Erro ao gerar presigned URL')
        return responder(500, {'success': False, 'message': 'Erro ao gerar URL'})

    return responder(200, {'success': True, 'download_url': url, 'status': status, 'record_id': record_id})


def obter_id_registro(event):
    params = event.get('pathParameters') or {}
    return params.get('filename') or params.get('id')

def buscar_registro(table, record_id):
    try:
        # O record_id é composto por "email_uploadId"
        email, upload_id = record_id.rsplit('_', 1)
        resp = table.get_item(Key={'idEmail': email, 'idUpload': upload_id})
        return resp.get('Item')
    except (ValueError, AttributeError) as e:
        logger.warning(f"Formato de ID inválido ou erro ao processar chave: {record_id}. Erro: {e}")
        return None

def gerar_url_presignada(s3_key):
    s3 = boto3.client('s3')
    try:
        return s3.generate_presigned_url('get_object', Params={'Bucket': S3_BUCKET, 'Key': s3_key}, ExpiresIn=3600)
    except Exception:
        return None

def responder(status_code, body_dict):
    return {
        'statusCode': status_code,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps(body_dict)
    }

def validar_jwt(id_token):
            # O 'id_token' contém os dados do perfil do usuário
            id_token = tokens.get('id_token')

            # 5. Decodificar o ID Token para ver os dados (Email, Sub, etc)
            # O ID Token é um JWT. A parte do meio (índice 1) contém os dados.
            payload_b64 = id_token.split('.')[1]
            # Adiciona padding se necessário para o base64
            payload_json = base64.b64decode(payload_b64 + '===').decode('utf-8')
            user_data = json.loads(payload_json)
            user_email = user_data.get('email')
            logger.info(f"Email: {user_email}")

            return user_email

    except urllib.error.HTTPError as e:
        error_details = e.read().decode()
        logger.error(f"Erro detalhado do Cognito: {error_details}")
        return None