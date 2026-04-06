# SSD Agent Minimal Fileset for Linux Binary Building

## Required Files

The following files constitute the minimal set required to build the SSD Agent binary on Linux:

### Core Application
- `agent_server.py` - Main Flask application
- `config.py` - Configuration settings
- `requirements.txt` - Python dependencies
- `build.sh` - Build script

### Module Directories
- `collectors/` - Hardware monitoring collectors
  - `cpu_collector.py`
  - `disk_collector.py`
  - `memory_collector.py`
  - `network_collector.py`
  - `smart_collector.py`
  - `system_collector.py`
- `executor/` - Task execution module
  - `fio_runner.py`
  - `__init__.py`

### Documentation
- `DEPLOYMENT.md` - Deployment guide with supervisor configuration
- `README.md` - Project documentation

## Build Process

On your Linux target system:

1. Ensure Python 3.12+ is installed
2. Transfer all required files to the target system
3. Make the build script executable: `chmod +x build.sh`
4. Run the build script: `./build.sh`
5. The resulting binary will be in the `dist/ssd-agent` file

## Supervisor Configuration

After building, configure supervisor to manage the service automatically:

1. Create supervisor config file: `/etc/supervisor/conf.d/ssd-agent.conf`
2. Configure with the command pointing to the built binary
3. Reload supervisor configuration
4. Start the service

See DEPLOYMENT.md for detailed instructions.