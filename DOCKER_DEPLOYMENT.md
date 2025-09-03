# Docker Deployment Guide

This guide explains how to deploy the Expense Tracker application using Docker.

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+ (optional, for easier management)

## Quick Start

### Option 1: Docker Compose (Recommended)

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd openhands-expense-calculator
   ```

2. **Start the application**:
   ```bash
   docker-compose up -d
   ```

3. **Access the application**:
   Open your browser and navigate to `http://localhost:8501`

4. **Stop the application**:
   ```bash
   docker-compose down
   ```

### Option 2: Docker Build and Run

1. **Build the image**:
   ```bash
   docker build -t expense-tracker .
   ```

2. **Run the container**:
   ```bash
   docker run -d \
     --name expense-tracker \
     -p 8501:8501 \
     -v $(pwd)/data:/app/data \
     expense-tracker
   ```

3. **Access the application**:
   Open your browser and navigate to `http://localhost:8501`

## Data Persistence

The application uses SQLite database for data storage. To ensure data persistence:

- **Docker Compose**: Data is automatically persisted in `./data` directory
- **Docker Run**: Use volume mount `-v $(pwd)/data:/app/data`

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `STREAMLIT_SERVER_PORT` | `8501` | Port for the web application |
| `STREAMLIT_SERVER_ADDRESS` | `0.0.0.0` | Server bind address |
| `STREAMLIT_SERVER_HEADLESS` | `true` | Run without browser |
| `STREAMLIT_BROWSER_GATHER_USAGE_STATS` | `false` | Disable usage stats |

### Custom Configuration

Create a `.env` file in the project root:

```env
STREAMLIT_SERVER_PORT=8080
STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
```

Then use with Docker Compose:

```bash
docker-compose --env-file .env up -d
```

## Health Monitoring

The container includes a health check that monitors the application status:

```bash
# Check container health
docker ps

# View health check logs
docker inspect expense-tracker | grep -A 10 Health
```

## Troubleshooting

### Container Won't Start

1. **Check logs**:
   ```bash
   docker logs expense-tracker
   ```

2. **Verify port availability**:
   ```bash
   netstat -tulpn | grep 8501
   ```

3. **Check file permissions**:
   ```bash
   ls -la data/
   ```

### Database Issues

1. **Reset database**:
   ```bash
   docker-compose down
   rm -rf data/expenses.db
   docker-compose up -d
   ```

2. **Backup database**:
   ```bash
   cp data/expenses.db data/expenses_backup_$(date +%Y%m%d).db
   ```

### Performance Issues

1. **Monitor resource usage**:
   ```bash
   docker stats expense-tracker
   ```

2. **Increase memory limit**:
   ```yaml
   # In docker-compose.yml
   services:
     expense-tracker:
       deploy:
         resources:
           limits:
             memory: 512M
   ```

## Security Considerations

- The application runs as a non-root user (`appuser`)
- No sensitive data is exposed in environment variables
- Database files are stored in mounted volumes with proper permissions
- CORS and XSRF protection are configured for container deployment

## Production Deployment

For production deployment, consider:

1. **Use a reverse proxy** (nginx, traefik) for SSL termination
2. **Set up monitoring** (Prometheus, Grafana)
3. **Configure log aggregation** (ELK stack, Fluentd)
4. **Implement backup strategy** for database files
5. **Use Docker secrets** for sensitive configuration

### Example with Nginx

```yaml
version: '3.8'
services:
  expense-tracker:
    build: .
    expose:
      - "8501"
    volumes:
      - ./data:/app/data
    
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - expense-tracker
```

## Maintenance

### Updates

1. **Pull latest changes**:
   ```bash
   git pull origin main
   ```

2. **Rebuild and restart**:
   ```bash
   docker-compose down
   docker-compose build --no-cache
   docker-compose up -d
   ```

### Cleanup

1. **Remove unused images**:
   ```bash
   docker image prune -f
   ```

2. **Clean up volumes** (⚠️ This will delete data):
   ```bash
   docker-compose down -v
   ```

## Support

For issues related to Docker deployment:

1. Check the application logs: `docker logs expense-tracker`
2. Verify Docker and Docker Compose versions
3. Ensure proper file permissions on mounted volumes
4. Check firewall settings for port 8501