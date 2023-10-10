import json
from dataclasses import dataclass, field

@dataclass
class RabbitAnswer:
    path: str | None
    upload_id: int
    json: str = field(init=False)
    
    def __post_init__(self):
        self.json = json.dumps(
            {
                'path': self.path,
                'upload_id': self.upload_id
            },
            ensure_ascii=False)