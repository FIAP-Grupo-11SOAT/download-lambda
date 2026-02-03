import unittest
from unittest.mock import patch, MagicMock
import os
import sys
import json
import logging
import importlib

# Adiciona o diretório pai ao sys.path para permitir a importação do módulo principal
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Importa o módulo usando importlib devido ao hífen no nome do arquivo
download_function = importlib.import_module("download-function")

class TestDownloadFunction(unittest.TestCase):

    def setUp(self):
        # Configura variáveis de ambiente simuladas no módulo para cada teste
        download_function.S3_BUCKET = 'test-bucket'
        download_function.TABLE_NAME = 'test-table'
        
        # Silencia o logger durante os testes para não poluir a saída
        download_function.logger.setLevel(logging.CRITICAL)

    def test_missing_bucket_env(self):
        download_function.S3_BUCKET = None
        response = download_function.lambda_handler({}, None)
        self.assertEqual(response['statusCode'], 500)
        body = json.loads(response['body'])
        self.assertIn('Variável de ambiente BUCKET não configurada', body['message'])

    def test_missing_table_env(self):
        download_function.TABLE_NAME = None
        response = download_function.lambda_handler({}, None)
        self.assertEqual(response['statusCode'], 500)
        body = json.loads(response['body'])
        self.assertIn('Variável de ambiente TABLE não configurada', body['message'])

    def test_missing_id_param(self):
        event = {'pathParameters': {}}
        response = download_function.lambda_handler(event, None)
        self.assertEqual(response['statusCode'], 400)
        body = json.loads(response['body'])
        self.assertIn('Parâmetro id/filename ausente', body['message'])

    @patch('boto3.resource')
    def test_record_not_found(self, mock_dynamo_resource):
        # Mock da tabela DynamoDB
        mock_table = MagicMock()
        mock_dynamo_resource.return_value.Table.return_value = mock_table
        mock_table.get_item.return_value = {} # Simula item não encontrado (vazio)

        event = {'pathParameters': {'filename': 'user@example.com_12345'}}
        response = download_function.lambda_handler(event, None)

        self.assertEqual(response['statusCode'], 404)
        body = json.loads(response['body'])
        self.assertIn('Registro não encontrado', body['message'])

    @patch('boto3.resource')
    def test_record_found_no_s3_key(self, mock_dynamo_resource):
        mock_table = MagicMock()
        mock_dynamo_resource.return_value.Table.return_value = mock_table
        # Simula item encontrado mas sem s3_key (ainda processando)
        mock_table.get_item.return_value = {
            'Item': {
                'idEmail': 'user@example.com',
                'idUpload': '12345',
                'status': 'PROCESSING'
            }
        }

        event = {'pathParameters': {'filename': 'user@example.com_12345'}}
        response = download_function.lambda_handler(event, None)

        self.assertEqual(response['statusCode'], 400)
        body = json.loads(response['body'])
        self.assertIn('sem arquivo disponível ainda', body['message'])

    @patch('boto3.client')
    @patch('boto3.resource')
    def test_success_download_url(self, mock_dynamo_resource, mock_s3_client):
        # Mock DynamoDB retornando registro completo
        mock_table = MagicMock()
        mock_dynamo_resource.return_value.Table.return_value = mock_table
        mock_table.get_item.return_value = {
            'Item': {
                'idEmail': 'user@example.com',
                'idUpload': '12345',
                'status': 'DONE',
                's3_key': 'outputs/video.zip'
            }
        }

        # Mock S3 gerando URL assinada
        expected_url = 'https://s3.amazonaws.com/bucket/outputs/video.zip?signature=xyz'
        mock_s3_client.return_value.generate_presigned_url.return_value = expected_url

        event = {'pathParameters': {'filename': 'user@example.com_12345'}}
        response = download_function.lambda_handler(event, None)

        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        self.assertTrue(body['success'])
        self.assertEqual(body['download_url'], expected_url)
        self.assertEqual(body['record_id'], 'user@example.com_12345')

if __name__ == '__main__':
    unittest.main()