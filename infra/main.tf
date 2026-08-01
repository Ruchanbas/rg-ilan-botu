terraform {
  required_version = ">= 1.5"
  required_providers {
    aws     = { source = "hashicorp/aws", version = "~> 5.0" }
    archive = { source = "hashicorp/archive", version = "~> 2.4" }
  }
}

provider "aws" {
  region = var.bolge
}

variable "bolge" {
  description = "AWS bölgesi"
  type        = string
  default     = "eu-central-1"
}

variable "alarm_email" {
  description = "Hata alarmlarının gideceği e-posta"
  type        = string
}

variable "github_repo" {
  description = "GitHub deposu: kullanici/depo"
  type        = string
}

variable "kuru_calisma" {
  description = "true iken WhatsApp'a gerçek mesaj gitmez, sadece loglanır"
  type        = bool
  default     = true
}

locals {
  ad = "rgbot"
  # "Ruchanbas/rg-ilan-botu" -> owner="Ruchanbas", name="rg-ilan-botu"
  github_owner     = split("/", var.github_repo)[0]
  github_repo_name = split("/", var.github_repo)[1]
}

# ---------------------------------------------------------------------
# Lambda paketi
# ---------------------------------------------------------------------
# Zip + layer kullanıyoruz, container image DEĞİL: ECR depolama
# always-free listesinde yok. Zip'te kod depolama Lambda kotasına dahil.

data "archive_file" "kod" {
  type        = "zip"
  source_dir  = "${path.module}/../src"
  output_path = "${path.module}/build/kod.zip"
}

resource "aws_lambda_layer_version" "bagimliliklar" {
  layer_name          = "${local.ad}-bagimliliklar"
  filename            = "${path.module}/build/layer.zip"
  source_code_hash    = filebase64sha256("${path.module}/build/layer.zip")
  compatible_runtimes = ["python3.12"]
  description         = "requests, beautifulsoup4, pdfplumber"
}

# ---------------------------------------------------------------------
# DynamoDB — always free (25 GB, 25 RCU/WCU)
# ---------------------------------------------------------------------

resource "aws_dynamodb_table" "ilanlar" {
  name         = "${local.ad}-ilanlar"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "pdf_url"

  attribute {
    name = "pdf_url"
    type = "S"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }
}

# ---------------------------------------------------------------------
# SSM Parameter Store — Secrets Manager değil (o sır başına $0.40/ay)
# ---------------------------------------------------------------------

resource "aws_ssm_parameter" "wa_token" {
  name        = "/rgbot/wa_token"
  type        = "SecureString"
  value       = "DOLDURULACAK"
  description = "WhatsApp Cloud API kalıcı system user token"
  lifecycle { ignore_changes = [value] }
}

resource "aws_ssm_parameter" "wa_phone_id" {
  name        = "/rgbot/wa_phone_id"
  type        = "String"
  value       = "DOLDURULACAK"
  description = "WhatsApp test numarasinin Phone number ID degeri"
  lifecycle { ignore_changes = [value] }
}

resource "aws_ssm_parameter" "alicilar" {
  name        = "/rgbot/alicilar"
  type        = "String"
  value       = "[]"
  description = "JSON dizi: [\"905xxxxxxxxx\"]"
  lifecycle { ignore_changes = [value] }
}

# ---------------------------------------------------------------------
# IAM — en az yetki
# ---------------------------------------------------------------------

resource "aws_iam_role" "lambda" {
  name = "${local.ad}-lambda"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "lambda" {
  name = "${local.ad}-lambda"
  role = aws_iam_role.lambda.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = ["dynamodb:GetItem", "dynamodb:PutItem",
        "dynamodb:UpdateItem", "dynamodb:Scan"]
        Resource = aws_dynamodb_table.ilanlar.arn
      },
      {
        Effect   = "Allow"
        Action   = ["ssm:GetParameter", "ssm:GetParameters"]
        Resource = "arn:aws:ssm:${var.bolge}:*:parameter/rgbot/*"
      },
      {
        Effect   = "Allow"
        Action   = ["cloudwatch:PutMetricData"]
        Resource = "*"
      },
    ]
  })
}

# ---------------------------------------------------------------------
# Lambda fonksiyonları — VPC YOK (NAT Gateway ~$32/ay tuzağı)
# ---------------------------------------------------------------------

resource "aws_lambda_function" "bildirici" {
  function_name    = "${local.ad}-bildirici"
  role             = aws_iam_role.lambda.arn
  handler          = "rgbot.handler.bildirim_handler"
  runtime          = "python3.12"
  filename         = data.archive_file.kod.output_path
  source_code_hash = data.archive_file.kod.output_base64sha256
  timeout          = 60
  memory_size      = 256
  layers           = [aws_lambda_layer_version.bagimliliklar.arn]

  environment {
    variables = {
      RGBOT_TABLO        = aws_dynamodb_table.ilanlar.name
      RGBOT_KURU_CALISMA = tostring(var.kuru_calisma)
    }
  }
}

resource "aws_lambda_function" "hatirlatici" {
  function_name    = "${local.ad}-hatirlatici"
  role             = aws_iam_role.lambda.arn
  handler          = "rgbot.handler.hatirlatici_handler"
  runtime          = "python3.12"
  filename         = data.archive_file.kod.output_path
  source_code_hash = data.archive_file.kod.output_base64sha256
  timeout          = 60
  memory_size      = 256
  layers           = [aws_lambda_layer_version.bagimliliklar.arn]

  environment {
    variables = {
      RGBOT_TABLO        = aws_dynamodb_table.ilanlar.name
      RGBOT_KURU_CALISMA = tostring(var.kuru_calisma)
    }
  }
}

# Log grupları: saklama süresi ŞART. Varsayılan "sonsuza kadar" ve
# CloudWatch Logs ingestion ücretli — sessizce birikir.
resource "aws_cloudwatch_log_group" "bildirici" {
  name              = "/aws/lambda/${aws_lambda_function.bildirici.function_name}"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "hatirlatici" {
  name              = "/aws/lambda/${aws_lambda_function.hatirlatici.function_name}"
  retention_in_days = 30
}

# ---------------------------------------------------------------------
# Zamanlama — EventBridge Scheduler (timezone destekler, klasik rule UTC)
# ---------------------------------------------------------------------

resource "aws_iam_role" "scheduler" {
  name = "${local.ad}-scheduler"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "scheduler.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "scheduler" {
  name = "${local.ad}-scheduler"
  role = aws_iam_role.scheduler.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = "lambda:InvokeFunction"
      Resource = [aws_lambda_function.hatirlatici.arn]
    }]
  })
}

resource "aws_scheduler_schedule" "hatirlatma" {
  name                         = "${local.ad}-hatirlatma"
  schedule_expression          = "cron(30 9 * * ? *)"
  schedule_expression_timezone = "Europe/Istanbul"
  flexible_time_window { mode = "OFF" }
  target {
    arn      = aws_lambda_function.hatirlatici.arn
    role_arn = aws_iam_role.scheduler.arn
  }
}

# ---------------------------------------------------------------------
# Alarmlar — free tier 10 alarm veriyor, 4 kullanıyoruz
# ---------------------------------------------------------------------

resource "aws_sns_topic" "alarm" {
  name = "${local.ad}-alarm"
}

resource "aws_sns_topic_subscription" "alarm_email" {
  topic_arn = aws_sns_topic.alarm.arn
  protocol  = "email"
  endpoint  = var.alarm_email
}

resource "aws_cloudwatch_metric_alarm" "lambda_hata" {
  alarm_name          = "${local.ad}-lambda-hata"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 3600
  statistic           = "Sum"
  threshold           = 1
  dimensions          = { FunctionName = aws_lambda_function.bildirici.function_name }
  alarm_actions       = [aws_sns_topic.alarm.arn]
  alarm_description   = "Tarayıcı Lambda hata verdi"
}

# SESSİZ ÖLÜM ALARMI — scraper'ların asıl riski.
# Site HTML'ini değiştirir, kod patlamaz, sadece hiçbir şey bulamaz.
resource "aws_cloudwatch_metric_alarm" "sayfa_bulunamadi" {
  alarm_name          = "${local.ad}-sayfa-bulunamadi"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 3
  datapoints_to_alarm = 3
  metric_name         = "SayfaBulundu"
  namespace           = "RGBot"
  period              = 86400
  statistic           = "Sum"
  threshold           = 1
  treat_missing_data  = "breaching"
  alarm_actions       = [aws_sns_topic.alarm.arn]
  alarm_description   = "3 gün üst üste Çeşitli İlanlar sayfası bulunamadı"
}

resource "aws_cloudwatch_metric_alarm" "pdf_bulunamadi" {
  alarm_name          = "${local.ad}-pdf-bulunamadi"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 7
  datapoints_to_alarm = 7
  metric_name         = "PdfSayisi"
  namespace           = "RGBot"
  period              = 86400
  statistic           = "Sum"
  threshold           = 1
  treat_missing_data  = "breaching"
  alarm_actions       = [aws_sns_topic.alarm.arn]
  alarm_description   = "7 gün üst üste hiç PDF bulunamadı"
}

# ---------------------------------------------------------------------

output "bildirici_adi" { value = aws_lambda_function.bildirici.function_name }
output "hatirlatici_adi" { value = aws_lambda_function.hatirlatici.function_name }
output "tablo_adi" { value = aws_dynamodb_table.ilanlar.name }

# ---------------------------------------------------------------------
# GitHub Actions -> AWS erişimi (OIDC)
# ---------------------------------------------------------------------
# Statik erişim anahtarı GitHub'a KOYULMUYOR. Actions her çalıştığında
# GitHub'ın imzaladığı kısa ömürlü bir kimlik jetonu üretiliyor, AWS
# bunu doğrulayıp geçici kimlik veriyor. Sızdırılacak kalıcı sır yok.

resource "aws_iam_openid_connect_provider" "github" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]
}

resource "aws_iam_role" "github_actions" {
  name = "${local.ad}-github-actions"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = aws_iam_openid_connect_provider.github.arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "token.actions.githubusercontent.com:aud"        = "sts.amazonaws.com"
          "token.actions.githubusercontent.com:repository" = var.github_repo
        }
        # AWS, GitHub OIDC sağlayıcısı için "sub" (veya job_workflow_ref)
        # koşulunu ZORUNLU tutuyor. 15 Temmuz 2026 sonrası açılan
        # depolarda sub, depo adının yanına değişmez ID'ler ekliyor:
        #   repo:sahip@<ownerId>/depo@<repoId>:ref:...
        # Bu yüzden kalıp "repo:<sahip>@*/<depo>@*:*" biçiminde.
        StringLike = {
          "token.actions.githubusercontent.com:sub" = "repo:${local.github_owner}@*/${local.github_repo_name}@*:*"
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "github_actions" {
  name = "${local.ad}-github-actions"
  role = aws_iam_role.github_actions.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "lambda:InvokeFunction"
      Resource = aws_lambda_function.bildirici.arn
    }]
  })
}

output "github_rol_arn" {
  description = "GitHub'da AWS_ROLE_ARN secret'ina yazilacak deger"
  value       = aws_iam_role.github_actions.arn
}
