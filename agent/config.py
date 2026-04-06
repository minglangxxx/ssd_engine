import os


class Config:
    HOST = os.getenv('AGENT_HOST', '0.0.0.0')
    PORT = int(os.getenv('AGENT_PORT', '8080'))
    VERSION = os.getenv('AGENT_VERSION', '0.1.0')
