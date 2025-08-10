# Production Deployment Guide

## 🚀 Enhanced Meta-Analysis Chatbot - Production Ready

This guide covers deploying the enhanced meta-analysis chatbot in production environments.

## Prerequisites

- Docker 20.10+ and Docker Compose 2.0+
- At least 4GB RAM and 2 CPU cores
- OpenAI or Anthropic API key
- Linux/macOS/Windows with WSL2

## Quick Start

### 1. Clone and Setup

```bash
# Clone repository
git clone https://github.com/your-username/meta-analysis-chatbot.git
cd meta-analysis-chatbot

# Copy environment template
cp .env.example .env

# Edit .env with your API keys
nano .env
```

### 2. Build and Run with Docker Compose

```bash
# Build the enhanced image
docker-compose build

# Start the application
docker-compose up -d

# Check logs
docker-compose logs -f

# Access at http://localhost:7860
```

### 3. Health Monitoring

```bash
# Check health status
curl http://localhost:7860/health

# Detailed health check
curl http://localhost:7860/health/detailed

# Prometheus metrics
curl http://localhost:7860/metrics
```

## Production Configuration

### Environment Variables

Critical settings for production:

```env
# API Keys (required)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Security
SESSION_SECRET_KEY=generate-random-64-char-key
SECURE_COOKIES=true
RATE_LIMIT_PER_MINUTE=30

# Performance
RSCRIPT_TIMEOUT_SEC=300
MAX_SESSIONS=100
SESSION_TIMEOUT_HOURS=24

# Monitoring
LOG_LEVEL=INFO
ENABLE_METRICS=true
```

### Resource Limits

Configure in `docker-compose.yml`:

```yaml
deploy:
  resources:
    limits:
      cpus: '4'
      memory: 8G
    reservations:
      cpus: '2'
      memory: 4G
```

## Deployment Options

### Option 1: Single Server

```bash
# Use docker-compose for simple deployment
docker-compose up -d
```

### Option 2: Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: meta-analysis-chatbot
spec:
  replicas: 2
  selector:
    matchLabels:
      app: meta-analysis
  template:
    metadata:
      labels:
        app: meta-analysis
    spec:
      containers:
      - name: chatbot
        image: meta-analysis-chatbot:latest
        ports:
        - containerPort: 7860
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: api-keys
              key: openai
        resources:
          limits:
            memory: "4Gi"
            cpu: "2"
          requests:
            memory: "2Gi"
            cpu: "1"
        livenessProbe:
          httpGet:
            path: /health
            port: 7860
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 7860
          initialDelaySeconds: 10
          periodSeconds: 5
```

### Option 3: Cloud Platforms

#### AWS ECS

```bash
# Build and push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $ECR_URI
docker build -f Dockerfile.enhanced -t meta-analysis .
docker tag meta-analysis:latest $ECR_URI/meta-analysis:latest
docker push $ECR_URI/meta-analysis:latest

# Deploy with ECS CLI
ecs-cli compose --file docker-compose.yml service up
```

#### Google Cloud Run

```bash
# Build and push to GCR
gcloud builds submit --tag gcr.io/$PROJECT_ID/meta-analysis

# Deploy
gcloud run deploy meta-analysis \
  --image gcr.io/$PROJECT_ID/meta-analysis \
  --platform managed \
  --memory 4Gi \
  --cpu 2 \
  --port 7860 \
  --set-env-vars OPENAI_API_KEY=$OPENAI_API_KEY
```

#### Azure Container Instances

```bash
# Create container instance
az container create \
  --resource-group meta-analysis-rg \
  --name meta-analysis \
  --image meta-analysis-chatbot:latest \
  --cpu 2 \
  --memory 4 \
  --port 7860 \
  --environment-variables OPENAI_API_KEY=$OPENAI_API_KEY
```

## Monitoring & Observability

### 1. Application Logs

```bash
# View logs
docker-compose logs -f meta-analysis-chatbot

# Export logs
docker logs meta-analysis-enhanced > app.log
```

### 2. Prometheus Integration

Add to `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'meta-analysis'
    static_configs:
      - targets: ['localhost:7860']
    metrics_path: '/metrics'
```

### 3. Grafana Dashboard

Import the dashboard from `monitoring/grafana-dashboard.json` for:
- Request rates and latencies
- CPU/Memory usage
- R backend health
- Session statistics

## Security Best Practices

### 1. API Key Management

- Use secrets management (AWS Secrets Manager, HashiCorp Vault)
- Rotate keys regularly
- Never commit keys to version control

### 2. Network Security

```nginx
# Nginx reverse proxy configuration
server {
    listen 443 ssl http2;
    server_name meta-analysis.yourdomain.com;
    
    ssl_certificate /etc/ssl/certs/cert.pem;
    ssl_certificate_key /etc/ssl/private/key.pem;
    
    location / {
        proxy_pass http://localhost:7860;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /health {
        access_log off;
        proxy_pass http://localhost:7860/health;
    }
}
```

### 3. Rate Limiting

Configure in `.env`:

```env
RATE_LIMIT_PER_MINUTE=30
RATE_LIMIT_PER_HOUR=500
```

## Backup & Recovery

### 1. Session Backup

```bash
# Backup sessions
docker exec meta-analysis-enhanced tar -czf /tmp/sessions.tar.gz /app/sessions
docker cp meta-analysis-enhanced:/tmp/sessions.tar.gz ./backups/

# Restore sessions
docker cp ./backups/sessions.tar.gz meta-analysis-enhanced:/tmp/
docker exec meta-analysis-enhanced tar -xzf /tmp/sessions.tar.gz -C /
```

### 2. Database Backup (if using PostgreSQL)

```bash
# Backup
docker-compose exec postgres pg_dump -U metauser meta_analysis > backup.sql

# Restore
docker-compose exec -T postgres psql -U metauser meta_analysis < backup.sql
```

## Troubleshooting

### Common Issues

#### 1. R Backend Not Available

```bash
# Check R installation
docker exec meta-analysis-enhanced Rscript -e "sessionInfo()"

# Reinstall R packages
docker exec meta-analysis-enhanced Rscript /app/scripts/utils/install_packages.R
```

#### 2. High Memory Usage

```bash
# Check memory usage
docker stats meta-analysis-enhanced

# Increase memory limits in docker-compose.yml
# Restart with: docker-compose restart
```

#### 3. Session Recovery

```bash
# List recoverable sessions
docker exec meta-analysis-enhanced python -c "
from utils.error_handler import SessionRecoveryManager
manager = SessionRecoveryManager()
print(manager.list_recoverable_sessions())
"
```

### Debug Mode

Enable debug mode in `.env`:

```env
DEBUG=true
DEBUG_R=1
LOG_LEVEL=DEBUG
```

## Performance Tuning

### 1. Optimize R Backend

```r
# In scripts/utils/optimize.R
options(mc.cores = parallel::detectCores())
```

### 2. Enable Caching

```yaml
# Add Redis to docker-compose.yml
docker-compose --profile with-cache up -d
```

### 3. CDN for Static Assets

Use CloudFlare or AWS CloudFront for static file delivery.

## Scaling Strategies

### Horizontal Scaling

1. **Load Balancer**: Use HAProxy or Nginx
2. **Session Storage**: Move to Redis/PostgreSQL
3. **File Storage**: Use S3 or similar object storage

### Vertical Scaling

Increase resources in `docker-compose.yml`:

```yaml
resources:
  limits:
    cpus: '8'
    memory: 16G
```

## Maintenance

### Regular Tasks

- **Daily**: Check logs and health status
- **Weekly**: Review metrics and performance
- **Monthly**: Update dependencies and security patches
- **Quarterly**: Full backup and disaster recovery test

### Updates

```bash
# Pull latest changes
git pull origin main

# Rebuild and deploy
docker-compose build --no-cache
docker-compose up -d --force-recreate
```

## Support

- GitHub Issues: [Report bugs](https://github.com/your-username/meta-analysis-chatbot/issues)
- Documentation: Check `/docs` folder
- Health Check: `http://your-domain/health/detailed`

## License

MIT License - See LICENSE file for details.