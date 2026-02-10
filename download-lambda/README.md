# Download Lambda Service

Este projeto contém uma função AWS Lambda responsável por gerar URLs assinadas (Presigned URLs) para download seguro de arquivos processados. A função valida a autenticação do usuário via token JWT e verifica o status do processamento no DynamoDB antes de conceder o acesso.

## 📋 Funcionalidades

- **Autenticação:** Valida o token JWT (Bearer Token) e extrai o e-mail do usuário para garantir que ele só acesse seus próprios arquivos.
- **Verificação de Status:** Consulta o DynamoDB para confirmar se o arquivo já foi processado (`status: DONE`).
- **Segurança:** Gera uma URL assinada do S3 com tempo de expiração limitado (1 hora), permitindo o download direto sem expor o bucket publicamente.

## 🚀 Estrutura do Projeto

- `src/main/download-function.py`: Lógica principal da função Lambda.
- `src/main/tests/`: Testes unitários utilizando `unittest` e `mock`.
- `src/main/requirements.txt`: Dependências do projeto Python.
- `infra/`: Código Terraform para provisionamento da infraestrutura AWS.
- `.github/workflows/`: Pipelines de CI/CD para deploy automatizado.

## ⚙️ Configuração e Dependências

### Pré-requisitos
- Python 3.11+
- AWS CLI configurado
- Terraform (para deploy de infraestrutura)

### Variáveis de Ambiente
A função requer as seguintes variáveis de ambiente configuradas na AWS Lambda:

| Variável | Descrição |
|----------|-----------|
| `BUCKET` | Nome do bucket S3 onde os arquivos processados estão armazenados. |
| `TABLE`  | Nome da tabela DynamoDB contendo os metadados e status dos arquivos. |

## 🛠️ Instalação e Testes Locais

1. **Instale as dependências:**
   ```bash
   pip install -r src/main/requirements.txt
   ```

2. **Execute os testes unitários:**
   ```bash
   cd src/main
   python -m unittest tests/test_download_function.py
   ```

3. **Verifique a cobertura de testes:**
   ```bash
   coverage run -m unittest tests/test_download_function.py
   coverage report -m
   ```

## 📦 Deploy

O deploy é gerenciado automaticamente via **GitHub Actions** quando há um push na branch `main`. O workflow realiza os seguintes passos:
1. Instalação de dependências e execução dos testes.
2. Empacotamento da função Lambda.
3. Provisionamento/Atualização da infraestrutura via **Terraform**.

Para realizar o deploy manual da infraestrutura:
```bash
cd infra
terraform init
terraform apply
```

## 🔌 Exemplo de Uso (API)

**Requisição:**
- **Método:** `GET`
- **Path:** `/download/{filename}` (onde filename é composto por `email_uploadId`)
- **Headers:** `Authorization: Bearer <seu_token_jwt>`

**Resposta de Sucesso (200 OK):**
```json
{
  "success": true,
  "download_url": "https://s3.amazonaws.com/seu-bucket/outputs/video.zip?signature=...",
  "status": "DONE",
  "record_id": "user@example.com_12345"
}
```

**Erros Comuns:**
- `401 Unauthorized`: Token ausente ou inválido.
- `404 Not Found`: Registro não encontrado no banco de dados.
- `400 Bad Request`: Arquivo ainda em processamento ou ID inválido.
