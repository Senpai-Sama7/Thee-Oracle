# 🚀 Oracle Agent Deployment Guide

## 📋 Overview

This guide provides comprehensive deployment instructions for Oracle Agent v5.0-hardened in production environments.

## 🏗️ Architecture

### Components
- **Oracle Agent Core**: Main AI orchestration system
- **GUI Application**: Web-based management interface
- **Workflow Engine**: Enterprise automation system
- **Plugin System**: Extensible architecture
- **Integration Framework**: External service connections

### Deployment Options
- **Docker**: Containerized deployment
- **Kubernetes**: Orchestration at scale
- **Bare Metal**: Direct server deployment
- **Cloud**: AWS, GCP, Azure deployment

## 🐳 Docker Deployment

### Prerequisites
- Docker 20.10+
- Docker Compose 2.0+
- 4GB RAM minimum
- 2 CPU cores minimum

### Quick Start
```bash
# Clone repository
git clone https://github.com/oracle-agent/oracle-agent.git
cd oracle-agent

# Build and run
docker-compose up -d
```

### Dockerfile
```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash oracle
RUN chown -R oracle:oracle /app
USER oracle

# Expose ports
EXPOSE 5001 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Start application
CMD ["python", "main.py"]
```

### docker-compose.yml
```yaml
version: '3.8'

services:
  oracle-agent:
    build: .
    ports:
      - "5001:5001"
      - "8080:8080"
    environment:
      - GCP_PROJECT_ID=${GCP_PROJECT_ID}
      - ORACLE_MODEL_ID=${ORACLE_MODEL_ID:-gemini-2.0-flash-exp}
      - ORACLE_API_KEY=${ORACLE_API_KEY}
      - SECRET_KEY=${SECRET_KEY}
    volumes:
      - oracle_data:/app/data
      - oracle_logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped

  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=${POSTGRES_DB:-oracle_agent}
      - POSTGRES_USER=${POSTGRES_USER:-oracle}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    restart: unless-stopped

volumes:
  oracle_data:
  oracle_logs:
  redis_data:
  postgres_data:
```

## ☸️ Kubernetes Deployment

### Prerequisites
- Kubernetes 1.24+
- kubectl configured
- Helm 3.0+ (optional)

### Namespace
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: oracle-agent
  labels:
    name: oracle-agent
```

### ConfigMap
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: oracle-agent-config
  namespace: oracle-agent
data:
  ORACLE_MODEL_ID: "gemini-2.0-flash-exp"
  ORACLE_LOG_LEVEL: "INFO"
  ORACLE_MAX_TURNS: "20"
```

### Secret
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: oracle-agent-secrets
  namespace: oracle-agent
type: Opaque
data:
  GCP_PROJECT_ID: <base64-encoded-project-id>
  ORACLE_API_KEY: <base64-encoded-api-key>
  SECRET_KEY: <base64-encoded-secret-key>
  POSTGRES_PASSWORD: <base64-encoded-password>
```

### Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: oracle-agent
  namespace: oracle-agent
  labels:
    app: oracle-agent
spec:
  replicas: 3
  selector:
    matchLabels:
      app: oracle-agent
  template:
    metadata:
      labels:
        app: oracle-agent
    spec:
      containers:
      - name: oracle-agent
        image: oracle-agent:5.0.0-hardened
        ports:
        - containerPort: 5001
          name: gui
        - containerPort: 8080
          name: api
        envFrom:
        - configMapRef:
            name: oracle-agent-config
        - secretRef:
            name: oracle-agent-secrets
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
        volumeMounts:
        - name: data
          mountPath: /app/data
        - name: logs
          mountPath: /app/logs
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: oracle-agent-data
      - name: logs
        persistentVolumeClaim:
          claimName: oracle-agent-logs
```

### Service
```yaml
apiVersion: v1
kind: Service
metadata:
  name: oracle-agent-service
  namespace: oracle-agent
spec:
  selector:
    app: oracle-agent
  ports:
  - name: gui
    port: 5001
    targetPort: 5001
  - name: api
    port: 8080
    targetPort: 8080
  type: LoadBalancer
```

### Ingress
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: oracle-agent-ingress
  namespace: oracle-agent
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
  - hosts:
    - oracle-agent.example.com
    secretName: oracle-agent-tls
  rules:
  - host: oracle-agent.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: oracle-agent-service
            port:
              number: 5001
```

## ☁️ Cloud Deployment

### AWS Deployment

#### ECS Task Definition
```json
{
  "family": "oracle-agent",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "executionRoleArn": "arn:aws:iam::account:role/oracle-agent-execution-role",
  "taskRoleArn": "arn:aws:iam::account:role/oracle-agent-task-role",
  "containerDefinitions": [
    {
      "name": "oracle-agent",
      "image": "oracle-agent:5.0.0-hardened",
      "portMappings": [
        {
          "containerPort": 5001,
          "protocol": "tcp"
        },
        {
          "containerPort": 8080,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "GCP_PROJECT_ID",
          "value": "your-project-id"
        }
      ],
      "secrets": [
        {
          "name": "ORACLE_API_KEY",
          "valueFrom": {
            "secretArn": "arn:aws:secretsmanager:region:account:secret:oracle-agent-api-key"
          }
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/oracle-agent",
          "awslogs-region": "us-west-2",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

#### CloudFormation Template
```yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: 'Oracle Agent Deployment Stack'

Parameters:
  InstanceType:
    Type: String
    Default: t3.medium
    AllowedValues: [t3.micro, t3.small, t3.medium, t3.large]
    Description: 'EC2 instance type'

Resources:
  OracleAgentSecurityGroup:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupDescription: 'Security group for Oracle Agent'
      SecurityGroupIngress:
        - IpProtocol: tcp
          FromPort: 5001
          ToPort: 5001
          CidrIp: 0.0.0.0/0
        - IpProtocol: tcp
          FromPort: 8080
          ToPort: 8080
          CidrIp: 0.0.0.0/0

  OracleAgentInstance:
    Type: AWS::EC2::Instance
    Properties:
      InstanceType: !Ref InstanceType
      ImageId: ami-0abcdef123456789
      SecurityGroups:
        - !Ref OracleAgentSecurityGroup
      UserData:
        Fn::Base64: |
          #!/bin/bash
          yum update -y
          yum install -y docker
          service docker start
          usermod -a -G docker ec2-user
          docker run -d \
            -p 5001:5001 \
            -p 8080:8080 \
            -e GCP_PROJECT_ID=your-project-id \
            oracle-agent:5.0.0-hardened

Outputs:
  InstanceId:
    Description: 'Instance ID of Oracle Agent'
    Value: !Ref OracleAgentInstance
  PublicIP:
    Description: 'Public IP address'
    Value: !GetAtt OracleAgentInstance.PublicIp
```

### GCP Deployment

#### Cloud Run Service
```yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: oracle-agent
  annotations:
    run.googleapis.com/ingress: all
spec:
  template:
    metadata:
      annotations:
        autoscaling.knative.dev/maxScale: "10"
        autoscaling.knative.dev/minScale: "1"
    spec:
      containerConcurrency: 10
      timeoutSeconds: 300
      containers:
      - image: gcr.io/your-project/oracle-agent:5.0.0-hardened
        ports:
        - containerPort: 8080
        env:
        - name: GCP_PROJECT_ID
          value: "your-project-id"
        - name: ORACLE_API_KEY
          valueFrom:
            secretKeyRef:
              name: oracle-agent-secrets
              key: api-key
        resources:
          limits:
            cpu: "1"
            memory: "2Gi"
```

### Azure Deployment

#### Container Instance
```yaml
apiVersion: 2021-03-01
location: East US
properties:
  containerGroup:
    name: oracle-agent
    containers:
    - name: oracle-agent
      properties:
        image: oracle-agent:5.0.0-hardened
        ports:
        - port: 5001
          protocol: TCP
        - port: 8080
          protocol: TCP
        environmentVariables:
        - name: GCP_PROJECT_ID
          value: your-project-id
        - name: ORACLE_API_KEY
          secureValue: your-api-key
        resources:
          requests:
            cpu: 1.0
            memoryInGb: 2.0
    osType: Linux
    restartPolicy: Always
    ipAddress:
      type: Public
      ports:
        - port: 5001
          protocol: TCP
        - port: 8080
          protocol: TCP
  type: Microsoft.ContainerInstance/containerGroups
```

## 🔧 Configuration

### Environment Variables
```bash
# Required
GCP_PROJECT_ID=your-project-id
ORACLE_MODEL_ID=gemini-2.0-flash-exp

# Security
ORACLE_API_KEY=your-secure-api-key
SECRET_KEY=your-secret-key

# Performance
ORACLE_MAX_TURNS=20
ORACLE_LOG_LEVEL=INFO
ORACLE_WORKERS=4

# Storage
GCS_BUCKET_NAME=oracle-agent-backups
ORACLE_PROJECT_ROOT=/data/oracle-agent

# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=oracle_agent
POSTGRES_USER=oracle
POSTGRES_PASSWORD=your-password

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your-redis-password

# GUI
FORCE_HTTPS=false
GUI_HOST=0.0.0.0
GUI_PORT=5001

# API
API_HOST=0.0.0.0
API_PORT=8080
```

### Configuration Files
```bash
# .env file
GCP_PROJECT_ID=your-project-id
ORACLE_API_KEY=your-secure-api-key
SECRET_KEY=your-secret-key
POSTGRES_PASSWORD=your-password
REDIS_PASSWORD=your-redis-password

# config.yaml
oracle:
  model:
    id: gemini-2.0-flash-exp
    max_turns: 20
    timeout: 30
  
  security:
    api_key_required: true
    rate_limiting:
      enabled: true
      requests_per_minute: 100
  
  performance:
    workers: 4
    cache_enabled: true
    cache_ttl: 300
```

## 🔒 Security

### SSL/TLS Setup
```bash
# Generate SSL certificates
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ssl/private.key \
  -out ssl/certificate.crt

# Configure Nginx
server {
    listen 443 ssl;
    server_name oracle-agent.example.com;
    
    ssl_certificate /path/to/ssl/certificate.crt;
    ssl_certificate_key /path/to/ssl/private.key;
    
    location / {
        proxy_pass http://localhost:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Firewall Configuration
```bash
# UFW (Ubuntu)
sudo ufw allow 5001/tcp
sudo ufw allow 8080/tcp
sudo ufw enable

# iptables
sudo iptables -A INPUT -p tcp --dport 5001 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 8080 -j ACCEPT
sudo iptables-save
```

### Authentication
```bash
# Generate API key
python3 -c "
import secrets
print(f'ORACLE_API_KEY={secrets.token_urlsafe(32)}')
"

# Set secure session key
python3 -c "
import secrets
print(f'SECRET_KEY={secrets.token_urlsafe(64)}')
"
```

## 📊 Monitoring

### Health Checks
```bash
# Application health
curl http://localhost:8080/health

# Detailed status
curl http://localhost:8080/status

# Metrics
curl http://localhost:8080/metrics
```

### Logging
```bash
# View logs
docker-compose logs -f oracle-agent

# Kubernetes logs
kubectl logs -f deployment/oracle-agent -n oracle-agent

# System logs
tail -f /var/log/oracle-agent/app.log
```

### Monitoring Stack
```yaml
# docker-compose.monitoring.yml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana

  node-exporter:
    image: prom/node-exporter
    ports:
      - "9100:9100"
```

## 🚀 Scaling

### Horizontal Scaling
```yaml
# Kubernetes HPA
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: oracle-agent-hpa
  namespace: oracle-agent
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: oracle-agent
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### Vertical Scaling
```yaml
# Kubernetes VPA
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: oracle-agent-vpa
  namespace: oracle-agent
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: oracle-agent
  updatePolicy:
    updateMode: "Auto"
  resourcePolicy:
    containerPolicies:
    - containerName: oracle-agent
      maxAllowed:
        cpu: 2
        memory: 4Gi
      minAllowed:
        cpu: 250m
        memory: 512Mi
```

## 🔧 Troubleshooting

### Common Issues

#### Container Won't Start
```bash
# Check logs
docker logs oracle-agent

# Check resource usage
docker stats

# Check configuration
docker exec oracle-agent env | grep ORACLE
```

#### Connection Issues
```bash
# Test API connectivity
curl -I http://localhost:8080/health

# Check port availability
netstat -tlnp | grep :5001
netstat -tlnp | grep :8080

# Check firewall
sudo ufw status
```

#### Performance Issues
```bash
# Monitor resources
htop
iotop
df -h

# Profile application
python -m cProfile -o profile.stats main.py

# Check database connections
ps aux | grep postgres
```

### Debug Mode
```bash
# Enable debug logging
export ORACLE_LOG_LEVEL=DEBUG

# Run with verbose output
python3 main.py --verbose

# Enable debug endpoints
export ORACLE_DEBUG=true
```

## 📋 Maintenance

### Backup Strategy
```bash
# Database backup
pg_dump oracle_agent > backup_$(date +%Y%m%d).sql

# File system backup
tar -czf oracle_agent_backup_$(date +%Y%m%d).tar.gz /data/oracle-agent

# Configuration backup
cp .env .env.backup.$(date +%Y%m%d)
cp config.yaml config.yaml.backup.$(date +%Y%m%d)
```

### Update Process
```bash
# Pull latest version
git pull origin main

# Update dependencies
pip install -r requirements.txt

# Run migrations
python3 manage.py migrate

# Restart service
docker-compose restart oracle-agent
```

### Health Monitoring
```bash
# Create health check script
cat > health_check.sh << 'EOF'
#!/bin/bash
response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/health)
if [ $response -eq 200 ]; then
    echo "Oracle Agent is healthy"
    exit 0
else
    echo "Oracle Agent is unhealthy (HTTP $response)"
    exit 1
fi
EOF

chmod +x health_check.sh
```

---

## 🚀 Oracle Agent Deployment Guide - Production-Ready Deployment Instructions
