# SSD Agent Deployment Guide

## Building on Linux

1. Copy all files from this directory to your Linux machine
2. Ensure Python 3.12+ is installed
3. Run the build script:
   ```bash
   chmod +x build.sh
   ./build.sh
   ```

## Running with Supervisor

After building, configure supervisor to manage the agent process:

1. Install supervisor if not already installed:
   ```bash
   sudo apt-get install supervisor  # On Debian/Ubuntu
   # OR
   sudo yum install supervisor      # On CentOS/RHEL
   ```

2. Create the supervisor configuration file:
   ```bash
   sudo nano /etc/supervisor/conf.d/ssd-agent.conf
   ```

3. Add the following configuration:
   ```ini
   [program:ssd-agent]
   command=/full/path/to/your/agent/directory/dist/ssd-agent
   directory=/full/path/to/your/agent/directory
   autostart=true
   autorestart=true
   stdout_logfile=/var/log/supervisor/ssd-agent.log
   stderr_logfile=/var/log/supervisor/ssd-agent-error.log
   environment=AGENT_HOST="0.0.0.0",AGENT_PORT="8080",AGENT_VERSION="0.1.0"
   user=your-preferred-user
   ```

4. Update supervisor to recognize the new configuration:
   ```bash
   sudo supervisorctl reread
   sudo supervisorctl update
   sudo supervisorctl start ssd-agent
   ```

5. Verify the service is running:
   ```bash
   sudo supervisorctl status ssd-agent
   ```

## Configuration

The agent can be configured using environment variables:
- `AGENT_HOST`: Host to bind to (default: 0.0.0.0)
- `AGENT_PORT`: Port to listen on (default: 8080)
- `AGENT_VERSION`: Agent version string (default: 0.1.0)

## Managing the Service

Common supervisor commands:
- Start: `sudo supervisorctl start ssd-agent`
- Stop: `sudo supervisorctl stop ssd-agent`
- Restart: `sudo supervisorctl restart ssd-agent`
- Status: `sudo supervisorctl status ssd-agent`
- View logs: `sudo supervisorctl tail ssd-agent`