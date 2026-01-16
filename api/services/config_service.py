from datetime import datetime
from sqlalchemy.orm import Session
from api.models.models import SystemConfig

class ConfigService:
    def __init__(self, db: Session):
        self.db = db

    def get_config(self, key: str, default: str = None) -> str:
        config = self.db.query(SystemConfig).filter(
            SystemConfig.key == key, 
            SystemConfig.is_active == True
        ).first()
        
        if config:
            return config.value
        return default

    def set_config(self, key: str, value: str, description: str = None):
        config = self.db.query(SystemConfig).filter(SystemConfig.key == key).first()
        
        if config:
            config.value = value
            if description:
                config.updated_at = datetime.now()
        else:
            config = SystemConfig(key=key, value=value, description=description)
            self.db.add(config)
        
        self.db.commit()
        return config