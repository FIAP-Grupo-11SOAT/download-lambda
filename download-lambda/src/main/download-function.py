import os
import json
import logging
import boto3
import jwt
import requests
from jwt import PyJWKClient

logger = logging.getLogger()
logger.setLevel(logging.INFO)

S3_BUCKET = os.environ.get('BUCKET')
TABLE_NAME = os.environ.get('TABLE')

def validar_jwt_cognito(event):
    headers = event.get('headers') or {}
    auth_header = headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return False, 'Token JWT ausente ou mal formatado.'
    token = auth_header.split(' ')[1]
    COGNITO_USER_POOL_ID = os.environ.get('COGNITO_USER_POOL_ID')
    COGNITO_REGION = os.environ.get('COGNITO_REGION')
    COGNITO_ISSUER = f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}"
    COGNITO_JWKS_URL = f"{COGNITO_ISSUER}/.well-known/jwks.json"
    try:
        jwks_client = PyJWKClient(COGNITO_JWKS_URL)
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=None,
            issuer=COGNITO_ISSUER
        )
        return True, payload
    except Exception as e:
        return False, str(e)

def lambda_handler(event, context):
    """Handler Lambda para gerar URL de download (presigned).

    Espera `pathParameters.filename` contendo o nome do ZIP em `outputs/`.
    Retorna JSON com `download_url` em português.
    """
    # Validação Cognito JWT
    valido, info = validar_jwt_cognito(event)
    if not valido:
        return responder(401, {'success': False, 'message': f'Não autorizado: {info}'})

    if not S3_BUCKET:
        return responder(500, {'success': False, 'message': 'Variável de ambiente BUCKET não configurada'})

    if not TABLE_NAME:
        return responder(500, {'success': False, 'message': 'Variável de ambiente TABLE não configurada'})

    record_id = obter_id_registro(event)
    if not record_id:
        return responder(400, {'success': False, 'message': 'Parâmetro id/filename ausente'})

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
