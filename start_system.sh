#!/bin/bash

# Complete EC2 Deployment Script for Fraud Detection System
# Run this script on your EC2 instance

echo "Starting deployment of Fraud Detection System..."

# Update system
sudo yum update -y

# Install Python 3.9+ and pip
sudo yum install -y python3 python3-pip git nodejs npm

# Install system dependencies
sudo yum install -y gcc python3-devel

# Create application directory
sudo mkdir -p /opt/fraud-detection
sudo chown -R ec2-user:ec2-user /opt/fraud-detection
cd /opt/fraud-detection

# Create virtual environment for Python
python3 -m venv fraud_env
source fraud_env/bin/activate

# Install Python requirements
cat > requirements.txt << 'EOF'
kafka-python==2.0.2
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
scikit-learn==1.3.2
numpy==1.24.3
joblib==1.3.2
faker==20.1.0
requests==2.31.0
python-multipart==0.0.6
EOF

pip install -r requirements.txt

# Create directory structure
mkdir -p {backend,frontend,kafka,logs}

# Setup Kafka (if not already done)
if [ ! -d "/opt/kafka" ]; then
    echo "Setting up Kafka..."
    sudo yum install -y java-11-openjdk

    # Download Kafka
    cd /tmp
    wget https://downloads.apache.org/kafka/2.13-3.5.0/kafka_2.13-3.5.0.tgz
    sudo tar -xzf kafka_2.13-3.5.0.tgz -C /opt/
    sudo mv /opt/kafka_2.13-3.5.0 /opt/kafka
    sudo chown -R ec2-user:ec2-user /opt/kafka

    # Create Kafka directories
    sudo mkdir -p /var/kafka-logs /var/zookeeper
    sudo chown -R ec2-user:ec2-user /var/kafka-logs /var/zookeeper

    # Configure Kafka
    cat > /opt/kafka/config/server.properties << EOF
broker.id=0
listeners=PLAINTEXT://0.0.0.0:9092
advertised.listeners=PLAINTEXT://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):9092
log.dirs=/var/kafka-logs
num.partitions=3
zookeeper.connect=localhost:2181
EOF

    # Start Kafka services
    nohup /opt/kafka/bin/zookeeper-server-start.sh /opt/kafka/config/zookeeper.properties > /opt/fraud-detection/logs/zookeeper.log 2>&1 &
    sleep 10
    nohup /opt/kafka/bin/kafka-server-start.sh /opt/kafka/config/server.properties > /opt/fraud-detection/logs/kafka.log 2>&1 &
    sleep 15

    # Create topic
    /opt/kafka/bin/kafka-topics.sh --create --topic transactions --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1
fi

cd /opt/fraud-detection

# Setup FastAPI backend
cat > backend/main.py << 'EOF'
# [Copy the FastAPI backend code here]
# Note: In actual deployment, you would copy the FastAPI code from the artifact
EOF

# Create systemd service for FastAPI
sudo tee /etc/systemd/system/fraud-api.service > /dev/null << 'EOF'
[Unit]
Description=Fraud Detection FastAPI
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/opt/fraud-detection/backend
Environment="PATH=/opt/fraud-detection/fraud_env/bin"
ExecStart=/opt/fraud-detection/fraud_env/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

# Setup React frontend
mkdir -p frontend
cd frontend

# Initialize React app
npx create-react-app . --template typescript
npm install recharts lucide-react

# Replace default App.js with our dashboard
cat > src/App.js << 'EOF'
// [Copy the React frontend code here]
// Note: In actual deployment, you would copy the React code from the artifact
EOF

# Build React app
npm run build

# Setup Nginx for React app
sudo yum install -y nginx

sudo tee /etc/nginx/conf.d/fraud-detection.conf > /dev/null << 'EOF'
server {
    listen 80;
    server_name _;

    # Serve React app
    location / {
        root /opt/fraud-detection/frontend/build;
        index index.html index.htm;
        try_files $uri $uri/ /index.html;
    }

    # Proxy API requests to FastAPI
    location /api/ {
        proxy_pass http://localhost:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

# Configure firewall
sudo firewall-cmd --permanent --add-port=80/tcp
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --permanent --add-port=9092/tcp
sudo firewall-cmd --permanent --add-port=2181/tcp
sudo firewall-cmd --reload

# Create startup script for the complete system
cat > /opt/fraud-detection/start_system.sh << 'EOF'
#!/bin/bash
cd /opt/fraud-detection

echo "Starting Fraud Detection System..."

# Start Kafka (if not running)
if ! pgrep -f "kafka.Kafka" > /dev/null; then
    echo "Starting Kafka..."
    nohup /opt/kafka/bin/zookeeper-server-start.sh /opt/kafka/config/zookeeper.properties > logs/zookeeper.log 2>&1 &
    sleep 10
    nohup /opt/kafka/bin/kafka-server-start.sh /opt/kafka/config/server.properties > logs/kafka.log 2>&1 &
    sleep 15
fi

# Start FastAPI
echo "Starting FastAPI backend..."
sudo systemctl start fraud-api
sudo systemctl enable fraud-api

# Start Nginx
echo "Starting Nginx..."
sudo systemctl start nginx
sudo systemctl enable nginx

# Start Kafka producer (in background)
echo "Starting Kafka producer..."
source fraud_env/bin/activate
nohup python3 kafka/producer.py > logs/producer.log 2>&1 &

# Start Kafka consumer (in background)
echo "Starting Kafka consumer..."
nohup python3 kafka/consumer.py > logs/consumer.log 2>&1 &

echo "System started! Access dashboard at http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)"
EOF

chmod +x /opt/fraud-detection/start_system.sh

# Create stop script
cat > /opt/fraud-detection/stop_system.sh << 'EOF'
#!/bin/bash
echo "Stopping Fraud Detection System..."

# Stop services
sudo systemctl stop fraud-api
sudo systemctl stop nginx

# Stop Kafka processes
pkill -f "kafka.Kafka"
pkill -f "zookeeper"
pkill -f "producer.py"
pkill -f "consumer.py"

echo "System stopped!"
EOF

chmod +x /opt/fraud-detection/stop_system.sh

echo "Deployment complete!"
echo ""
echo "To start the system:"
echo "  /opt/fraud-detection/start_system.sh"
echo ""
echo "To stop the system:"
echo "  /opt/fraud-detection/stop_system.sh"
echo ""
echo "Logs are available in: /opt/fraud-detection/logs/"
echo ""
echo "Next steps:"
echo "1. Copy your Python code files to the appropriate directories"
echo "2. Copy your React code to frontend/src/App.js"
echo "3. Run the start script"
echo "4. Access your dashboard at http://YOUR-EC2-PUBLIC-IP"